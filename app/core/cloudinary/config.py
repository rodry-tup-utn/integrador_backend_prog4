from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudinarySettings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    CLOUDINARY_FOLDER: str = "food_store"


cloudinary_settings = CloudinarySettings()
