from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    supabase_url: str
    supabase_key: str
    elevenlabs_api_key: str
    tavily_api_key: str

    environment: str = "development"

    # Translation backend.
    #   "groq"  -> remote Groq LLM. No local model, ~600 MB RAM, fast, free tier friendly.
    #   "nllb"  -> local facebook/nllb-200-distilled-600M. Offline, but ~2.3 GB of
    #              weights and needs 3+ GB RAM. Use on beefier hosts.
    #   "auto"  -> prefer Groq, fall back to local NLLB if Groq fails.
    translation_backend: str = "groq"

    nllb_model_name: str = "facebook/nllb-200-distilled-600M"

    rate_limit_per_minute: int = 20

    # Comma-separated list of allowed browser origins, e.g.
    #   CORS_ORIGINS=https://my-app.vercel.app,https://my-app-git-main.vercel.app
    # Left empty the API accepts any origin, which is convenient locally but
    # not something you want on a public deployment.
    cors_origins: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()