from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongo_uri: str
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openrouter_api_key: str
    model_config = SettingsConfigDict(env_file="./.env")

settings = Settings()


