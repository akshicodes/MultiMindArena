from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str
    openrouter_api_key: str
    elevenlab_api_key: Optional[str] = None
    tts_default_provider: str = "edge"
    tts_fallback_to_edge: bool = True
    model_config = SettingsConfigDict(env_file="./.env")


settings = Settings()


