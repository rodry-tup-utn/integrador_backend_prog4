from pydantic_settings import BaseSettings, SettingsConfigDict


class MercadoPagoSettings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MP_ACCESS_TOKEN: str
    MP_PUBLIC_KEY: str | None = None
    MP_WEBHOOK_SECRET: str

    FRONTEND_SUCCESS_URL: str
    FRONTEND_FAILURE_URL: str
    FRONTEND_PENDING_URL: str

    BACKEND_NOTIFICATION_URL: str


mp_settings = MercadoPagoSettings()
