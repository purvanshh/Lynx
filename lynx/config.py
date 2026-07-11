from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lynx Candidate Identification System"
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    llm_enabled: bool = True
    llm_model: str = "gpt-4o-mini"
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str | None = None
    llm_request_timeout_seconds: float = 15.0
    llm_rate_limit_seconds: int = 60

    model_config = SettingsConfigDict(env_prefix="LYNX_", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
