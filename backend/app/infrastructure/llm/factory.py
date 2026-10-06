from functools import cache
from typing import TypeAlias

from langchain_openai import ChatOpenAI

from core.config import settings
from .models import AllModelEnum, OpenAIModelName

_MODEL_TABLE = {OpenAIModelName.GPT_5_6_SOL: "gpt-5.6-sol"}
ModelT: TypeAlias = ChatOpenAI


@cache
def get_model(model_name: AllModelEnum | str | None, /) -> ModelT:
    requested_name = model_name or settings.DEFAULT_MODEL or settings.OPENAI_MODEL or OpenAIModelName.GPT_5_6_SOL
    api_model_name = _MODEL_TABLE.get(requested_name)
    if api_model_name is None and isinstance(requested_name, str) and requested_name.startswith("gpt-"):
        api_model_name = requested_name
    if not api_model_name:
        raise ValueError(f"不支持的模型：{requested_name}")
    return ChatOpenAI(
        model=api_model_name, temperature=0.5, streaming=False, max_retries=3,
        timeout=60, api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL,
    )
