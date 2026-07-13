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

    confidence_high_threshold: float = 0.85
    confidence_medium_threshold: float = 0.65
    confidence_low_threshold: float = 0.45

    agent_weight_name_matcher: float = 0.15
    agent_weight_temporal: float = 0.20
    agent_weight_behavioral: float = 0.25
    agent_weight_solo_window: float = 0.25
    agent_weight_face_consistency: float = 0.10
    agent_weight_llm_reasoning: float = 0.05
    agent_weight_screen_share: float = 0.05

    model_config = SettingsConfigDict(env_prefix="LYNX_", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
