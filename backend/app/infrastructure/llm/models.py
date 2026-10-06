from enum import StrEnum
from typing import TypeAlias


class OpenAIModelName(StrEnum):
    GPT_5_6_SOL = "gpt-5.6-sol"


AllModelEnum: TypeAlias = OpenAIModelName | str
