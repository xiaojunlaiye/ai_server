from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import logging
import tempfile
import os
import base64
import json
import httpx
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech_to_text", tags=["speech_to_text"])


class SpeechToTextResponse(BaseModel):
    text: str


# 同时支持有无尾随斜杠的两种路径
@router.post("/", response_model=SpeechToTextResponse)
@router.post("", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(..., description="Language code (e.g., 'zh', 'en')")
) -> SpeechToTextResponse:
    """
    Convert speech to text using OpenAI Whisper API
    """
    try:
        logger.info(f"=== Speech-to-Text Request ===")
        logger.info(f"Audio filename: {audio.filename}")
        logger.info(f"Audio content type: {audio.content_type}")
        logger.info(f"Language: {language}")
        
        # 读取音频文件内容
        audio_content = await audio.read()
        logger.info(f"Audio file size: {len(audio_content)} bytes")
        
        # 将原始音频持久化到 /app/logs/uploads 以便人工核验
        try:
            uploads_dir = "/app/logs/uploads"
            os.makedirs(uploads_dir, exist_ok=True)
            # 使用时间戳+原始文件名，尽量避免重名
            from datetime import datetime
            safe_name = (audio.filename or "audio.wav").replace("/", "_")
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
            saved_path = os.path.join(uploads_dir, f"{ts}_{safe_name}")
            with open(saved_path, "wb") as f:
                f.write(audio_content)
            logger.info(f"Saved uploaded audio to: {saved_path}")
        except Exception as e:
            logger.warning(f"Failed to persist uploaded audio: {e}")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # 优先调用通义千问 Qwen3 ASR Flash（DashScope 多模态生成接口）
            tongyi_api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("TONGYI_API_KEY")
            if not tongyi_api_key:
                raise RuntimeError("DASHSCOPE_API_KEY/TONGYI_API_KEY is not set")

            # 将音频转为 base64，按 DashScope ASR 接口规范请求
            with open(temp_file_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            # 参考官方 curl：multimodal-generation/generation
            # 使用 base64 直接内联音频（无需公网 URL）
            enable_lid = not language or language.lower() in {"auto", ""}
            payload = {
                "model": "qwen3-asr-flash",
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": [{"text": ""}],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    # 与官网一致：audio 直接是字符串；此处用 data URL 内联
                                    "audio": f"data:audio/wav;base64,{audio_b64}"
                                }
                            ],
                        },
                    ]
                },
                "parameters": {
                    "asr_options": {
                        "enable_lid": enable_lid,
                        "enable_itn": False,
                    }
                }
            }

            headers = {
                "Authorization": f"Bearer {tongyi_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # 官方 DashScope 多模态生成 REST 接口
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            logger.info("Calling Tongyi Qwen ASR: qwen3-asr-flash")

            # 保存调用参数与响应到文件，便于排查（脱敏处理base64）
            try:
                os.makedirs("/app/logs/asr_calls", exist_ok=True)
                from datetime import datetime
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
                req_path = f"/app/logs/asr_calls/{ts}_request.json"
                # 复制并脱敏
                payload_for_log = json.loads(json.dumps(payload))
                # 脱敏 messages 中的 base64 音频（data URL）
                try:
                    msgs = payload_for_log.get("input", {}).get("messages", [])
                    for msg in msgs:
                        for item in msg.get("content", []):
                            audio_val = item.get("audio")
                            if isinstance(audio_val, str) and audio_val.startswith("data:audio"):
                                b64_part = audio_val.split(",", 1)[1] if "," in audio_val else ""
                                item["audio"] = {
                                    "base64_head": b64_part[:64],
                                    "total_len": len(b64_part),
                                }
                except Exception:
                    pass
                with open(req_path, "w", encoding="utf-8") as f:
                    json.dump(payload_for_log, f, ensure_ascii=False, indent=2)
                logger.info(f"ASR request saved: {req_path}")
            except Exception as e:
                logger.warning(f"Failed to save ASR request payload: {e}")

            try:
                # 记录请求开始时间
                request_start_time = time.time()
                logger.info(f"=== ASR Request Timing ===")
                logger.info(f"Request start time: {request_start_time}")
                
                # 使用更长的读取超时
                with httpx.Client(timeout=httpx.Timeout(connect=10, read=120, write=120, pool=10)) as client:
                    resp = client.post(url, headers=headers, data=json.dumps(payload))
                    
                # 记录响应接收时间
                response_end_time = time.time()
                request_duration = response_end_time - request_start_time
                logger.info(f"Response end time: {response_end_time}")
                logger.info(f"Total request duration: {request_duration:.3f} seconds")
                
                # 保存耗时信息到单独的日志文件
                try:
                    timing_log_path = f"/app/logs/asr_calls/{ts}_timing.json"
                    timing_data = {
                        "request_start_time": request_start_time,
                        "response_end_time": response_end_time,
                        "duration_seconds": round(request_duration, 3),
                        "language": language,
                        "audio_size_bytes": len(audio_content)
                    }
                    with open(timing_log_path, "w", encoding="utf-8") as f:
                        json.dump(timing_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Timing data saved: {timing_log_path}")
                except Exception as e:
                    logger.warning(f"Failed to save timing data: {e}")
                
                # 始终保存响应到文件，包含非200情况
                try:
                    resp_path = f"/app/logs/asr_calls/{ts}_response.json"
                    with open(resp_path, "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    logger.info(f"ASR response saved: {resp_path} (status={resp.status_code})")
                except Exception as e:
                    logger.warning(f"Failed to save ASR response: {e}")

                if resp.status_code != 200:
                    logger.error(f"Tongyi ASR error: {resp.status_code} {resp.text}")
                    return SpeechToTextResponse(text="翻译错误")

                data = resp.json()
                # 兼容通义返回：优先 output.choices[0].message.content[0].text
                text = (
                    (data.get("output", {}).get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content", [{}])[0]
                        .get("text")
                ) or (
                    (data.get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content", [{}])[0]
                        .get("text")
                ) or data.get("output", {}).get("text") or data.get("text") or ""
                if not text:
                    logger.warning(f"Tongyi ASR empty text, raw: {data}")
                    return SpeechToTextResponse(text="翻译错误")
                logger.info(f"ASR text: {text}")
                return SpeechToTextResponse(text=text)
            except Exception as e:
                # 将异常也落盘，便于排查
                try:
                    err_path = f"/app/logs/asr_calls/{ts}_exception.txt"
                    with open(err_path, "w", encoding="utf-8") as f:
                        f.write(str(e))
                    logger.error(f"ASR exception saved: {err_path}")
                except Exception:
                    pass
                logger.error(f"Tongyi ASR request failed: {e}")
                return SpeechToTextResponse(text="翻译错误")
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
                
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return SpeechToTextResponse(text="翻译错误")
