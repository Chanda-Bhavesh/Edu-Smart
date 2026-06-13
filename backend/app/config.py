from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "SCMS"
    app_env: str = "development"
    app_secret_key: str
    debug: bool = False

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    emails_from_email: str = "noreply@scms.edu"
    emails_from_name: str = "SCMS Platform"

    # Frontend — comma-separated list of allowed CORS origins
    frontend_url: str = "http://localhost:8080"
    allowed_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"

    # File Storage
    upload_dir: str = "uploads"
    max_file_size_mb: int = 10

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # AI / Claude API
    anthropic_api_key: str = ""           # set in .env to enable the chatbot
    ai_chat_model: str = "claude-haiku-4-5-20251001"
    ai_chat_max_tokens: int = 1024
    ai_chat_history_limit: int = 10       # messages of history sent to Claude


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
