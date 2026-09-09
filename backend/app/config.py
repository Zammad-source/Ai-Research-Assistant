from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    supabase_url: str
    supabase_key: str
    elevenlabs_api_key: str
    tavily_api_key: str

    environment: str = "development"

    nllb_model_name: str = "facebook/nllb-200-distilled-600M"

    chroma_persist_dir: str = "./chroma_store"

    # Kept for backward compatibility.
    # Retrieval is now handled by Tavily.
    wikipedia_lang: str = "en"

    rate_limit_per_minute: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()