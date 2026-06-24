from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session
import cloudinary.uploader
import logging
from uuid import uuid4

from app.core.cloudinary.config import cloudinary_settings
from app.modules.uploads.schemas import UploadResponse
from app.core.exceptions.custom_exceptions import BusinessRuleError

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class UploadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _validate_image_type(self, file: UploadFile) -> None:
        if file.content_type not in ALLOWED_TYPES:
            raise BusinessRuleError(
                message=f"Tipo de archivo no permitido: {file.content_type} - Se aceptan: {', '.join(ALLOWED_TYPES)}",
            )

    def _execute_upload(
        self, file: UploadFile, folder_suffix: str, public_id: str
    ) -> UploadResponse:
        folder = f"{cloudinary_settings.CLOUDINARY_FOLDER}/{folder_suffix}"

        try:
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            )
        except Exception:
            logger.exception(
                "Error al subir imagen a Cloudinary (folder=%s, public_id=%s)",
                folder,
                public_id,
            )
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo subir la imagen a Cloudinary",
            )

        return UploadResponse(
            url=result["secure_url"],
            public_id=result["public_id"],
        )

    def _delete_from_cloudinary(self, public_id: str) -> None:
        try:
            result = cloudinary.uploader.destroy(public_id, resouce_type="image")

            if result.get("result") not in ("ok", "not found"):
                logger.warning(
                    "Cloudinary devolvió un resultado inesperado al eliminar %s: %s",
                    public_id,
                    result,
                )
        except Exception:
            logger.exception(
                "Error al eliminar imagen de Cloudinary (public_id: %s)", public_id
            )

    def _get_public_id(self, url: str) -> str | None:
        try:
            upload_marker = "/upload/"
            idx = url.find(upload_marker)
            if idx == -1:
                return None

            after_upload = url[idx + len(upload_marker) :]

            if after_upload.startswith("v") and "/" in after_upload:
                after_upload = after_upload.split("/", 1)[1]

            public_id = after_upload.rsplit(".", 1)[0]
            return public_id

        except Exception:
            return None

    # ── Standalone upload (sin entidad) ──────────────────────────

    def upload_image(self, file: UploadFile) -> UploadResponse:
        self._validate_image_type(file)
        return self._execute_upload(
            file,
            folder_suffix="uploads",
            public_id=str(uuid4()),
        )

    def delete_image(self, public_id: str) -> None:
        self._delete_from_cloudinary(public_id)
