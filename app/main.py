import logging
import time
from logging.handlers import RotatingFileHandler
import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 访问日志到文件（轮转）
_access_logger = logging.getLogger("access")
try:
    import os
    os.makedirs("/app/logs", exist_ok=True)
    _file_handler = RotatingFileHandler("/app/logs/access.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    _file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    _access_logger.setLevel(logging.INFO)
    _access_logger.addHandler(_file_handler)
except Exception as _e:
    logging.getLogger(__name__).warning(f"Failed to init file handler for access log: {_e}")
    # 如果文件日志失败，至少记录到控制台
    _access_logger.addHandler(logging.StreamHandler())

# 读取 .env 环境变量（如存在）
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# CORS 配置
_default_origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    # Android 模拟器访问宿主机
    "http://10.0.2.2:3000",
    "http://10.0.2.2:8080",
]
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")
if ALLOWED_ORIGINS:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
else:
    origins = _default_origins

class ChatMessage(BaseModel):
    role: str = Field(..., description="one of system|user|assistant")
    content: str

class ChatRequest(BaseModel):
    model: str = Field("gpt-4o-mini")
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    # LLM 提供商选择
    provider: Optional[str] = None  # "openai" 或 "tongyi"
    # 允许透传额外参数
    extra: Dict[str, Any] = Field(default_factory=dict)

class ChatResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatResponse(BaseModel):
    id: Optional[str] = None
    choices: List[ChatResponseChoice]
    model: Optional[str] = None

app = FastAPI(title="LLM_api FastAPI Demo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简单请求访问日志中间件
@app.middleware("http")
async def access_log_middleware(request, call_next):
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        try:
            duration_ms = int((time.time() - start) * 1000)
            client_host = request.client.host if request.client else "-"
            method = request.method
            path = request.url.path
            status = getattr(response, "status_code", 0)
            _access_logger.info(f"client={client_host} method={method} path={path} status={status} duration_ms={duration_ms}")
        except Exception:
            pass

# --- Routers ---
from app.routers.translation import router as translation_router  # noqa: E402
from app.routers.xhs_hotpost import router as xhs_router  # noqa: E402
from app.routers.image_gen import router as image_router  # noqa: E402
from app.routers.speech_to_text import router as speech_router  # noqa: E402

app.include_router(translation_router)
app.include_router(xhs_router)
app.include_router(image_router)
app.include_router(speech_router)

# --- Direct endpoints for client compatibility ---
from app.services.translation import TranslationRequest, TranslationResponse, translate  # noqa: E402

@app.post("/translate", response_model=TranslationResponse)
def translate_direct(req: TranslationRequest) -> TranslationResponse:
    """Direct /translate endpoint for client compatibility"""
    try:
        return translate(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation error: {e}")


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    from app.common.llm_client import get_default_client, get_client_by_provider

    try:
        # 获取LLM客户端
        if req.provider:
            client = get_client_by_provider(req.provider)
        else:
            client = get_default_client()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize LLM client: {e}")

    # 设置默认模型
    if req.provider == "tongyi":
        default_model = req.model if req.model != "gpt-4o-mini" else "qwen-turbo"
    else:
        default_model = req.model

    try:
        # 构建请求参数
        kwargs = {
            "model": default_model,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            kwargs["max_tokens"] = req.max_tokens
        if req.extra:
            kwargs.update(req.extra)

        # 调用聊天完成API
        response = client.chat_completion(
            messages=[m.model_dump() for m in req.messages],
            **kwargs
        )

        # 构建响应
        choice = ChatResponseChoice(
            index=0,
            message=ChatMessage(role="assistant", content=response.get("text", "")),
            finish_reason=None,
        )

        return ChatResponse(
            id=response.get("id"),
            choices=[choice],
            model=response.get("model"),
        )

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
