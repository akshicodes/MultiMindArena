from pydantic import BaseModel, Field
from enum import Enum


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"


class LLMConfigModel(BaseModel):

    provider: ProviderType

    model_name: str

    api_keys: list[str]

    current_key_index: int = Field(
        ge=0
    )

    max_tokens: int = Field(
        gt=0
    )

    temperature: float = Field(
        ge=0,
        le=2
    )

    persona_prompts: dict[str, str]

    rate_limit_rpm: int = Field(
        gt=0
    )

    is_active: bool