import cloudinary
from app.core.cloudinary.config import cloudinary_settings


def init_cloudinary() -> None:

    cloudinary.config(
        cloud_name=cloudinary_settings.CLOUDINARY_CLOUD_NAME,
        api_key=cloudinary_settings.CLOUDINARY_API_KEY,
        api_secret=cloudinary_settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
