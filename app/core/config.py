from pydantic import computed_field
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):

    postgres_user: str = "admin"
    postgres_password: str = "admin"
    postgres_db: str = "db_integrador"
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    secret_key: str = "secret-key-dev"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    slow_request_threshold_ms: int = 500
    rate_limit_default_burst: int = 10
    rate_limit_default_per_minute: int = 60
    rate_limit_auth_burst: int = 3
    rate_limit_auth_per_minute: float = 0.333
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:5173"
    admin_email: str = "admin@admin.com"
    admin_pass: str = "admin1234"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    # URL directa de base de datos (prioritaria sobre postgres_* individuales).
    database_url: str | None = None

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Ignorar variables extra del .env que no sean campos declarados
        "extra": "ignore",
    }

    # URL específica para tests (SQLite in-memory por default).
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # ─── Logging ─────────────────────────────────────────────────────────────
    # Nivel de log. Literal evita typos (typo en el .env → falla validación).
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


settings = Settings()  # type: ignore
