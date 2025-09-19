import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")


def create_openai_client() -> Any:
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    kwargs: Dict[str, Any] = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL

    client = OpenAI(**kwargs)
    return client


def has_responses_api(client: Any) -> bool:
    return hasattr(client, "responses") and hasattr(client.responses, "create")
