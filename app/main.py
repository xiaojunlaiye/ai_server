import logging
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
        logging.StreamHandler()  # 输出到控制台
    ]
)

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
    # 允许透传额外 OpenAI 兼容参数
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

# --- Routers ---
from app.routers.translation import router as translation_router  # noqa: E402
from app.routers.xhs_hotpost import router as xhs_router  # noqa: E402
from app.routers.image_gen import router as image_router  # noqa: E402

app.include_router(translation_router)
app.include_router(xhs_router)
app.include_router(image_router)

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
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    client_kwargs: Dict[str, Any] = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        client_kwargs["base_url"] = OPENAI_BASE_URL

    client = OpenAI(**client_kwargs)

    # 如果可用优先使用 Responses API，否则回退到 Chat Completions
    use_responses_api = hasattr(client, "responses") and hasattr(client.responses, "create")

    try:
        if use_responses_api:
            # 将 messages 简单串联为一个输入，适配 Responses API
            prompt_segments: List[str] = [f"{m.role}: {m.content}" for m in req.messages]
            prompt: str = "\n".join(prompt_segments) if prompt_segments else "Hello"

            response = client.responses.create(
                model=req.model,
                input=prompt,
                temperature=req.temperature,
                max_output_tokens=req.max_tokens,
                **(req.extra or {}),
            )
            text_output: str = getattr(response, "output_text", None) or ""

            choice = ChatResponseChoice(
                index=0,
                message=ChatMessage(role="assistant", content=text_output),
                finish_reason=None,
            )

            return ChatResponse(
                id=getattr(response, "id", None),
                choices=[choice],
                model=getattr(response, "model", None),
            )
        else:
            # 回退：使用 Chat Completions 兼容路径
            response = client.chat.completions.create(
                model=req.model,
                messages=[m.model_dump() for m in req.messages],
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                **(req.extra or {}),
            )

            choices: List[ChatResponseChoice] = []
            for idx, choice in enumerate(response.choices):
                cmsg = choice.message
                choices.append(
                    ChatResponseChoice(
                        index=idx,
                        message=ChatMessage(role=cmsg.role, content=cmsg.content or ""),
                        finish_reason=getattr(choice, "finish_reason", None),
                    )
                )

            return ChatResponse(
                id=getattr(response, "id", None),
                choices=choices,
                model=getattr(response, "model", None),
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
