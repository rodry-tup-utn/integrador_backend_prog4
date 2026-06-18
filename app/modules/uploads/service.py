from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session
import cloudinary.uploader
import logging

from app.core.cloudinary.config import cloudinary_settings
from app.modules.uploads.schemas import UploadResponse
from app.modules.product.unit_of_work import ProductUnitOfWork
from app.modules.category.unit_of_work import CategoryUnitOfWork

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class UploadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # Helper que valida el tipo de archivo que se intenta subir
    def _validate_image_type(self, file: UploadFile) -> None:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido: {file.content_type} - Se aceptan: {', '.join(ALLOWED_TYPES)}",
            )

    # Método que ejecuta el upload de cloudinary y devuelve la url de la imagen y su public_id
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

    # Método que elimina una imagen de cloudinary por su public_id
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

    # Método para obtener la public_id de la url de Cloudinary
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

    # Método para subir a cloudinary la imagen de un producto y actualizar el campo en la tabla de product
    def upload_product_image(self, product_id: int, file: UploadFile) -> UploadResponse:
        self._validate_image_type(file)

        with ProductUnitOfWork(self._session) as uow:
            product = uow.products.get_by_id(product_id)
            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con id {product_id} no encontrado",
                )

            if product.images_url:
                old_public_id = self._get_public_id(product.images_url)

                if old_public_id:
                    self._delete_from_cloudinary(old_public_id)

            result = self._execute_upload(
                file,
                folder_suffix="products",
                public_id=str(product_id),
            )

            product.images_url = result.url
            uow.products.add(product)
        return result

    # Método para eliminar la imagen de un producto de cloudinary y limpiar el campo images_url
    def delete_product_image(self, product_id: int) -> None:
        with ProductUnitOfWork(self._session) as uow:
            product = uow.products.get_by_id(product_id)

            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con id {product_id} no encontrado",
                )

            if not product.images_url:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="El producto no tiene ninguna imagen asociada para eliminar",
                )

            public_id = self._get_public_id(product.images_url)
            if public_id:
                self._delete_from_cloudinary(public_id)

            product.images_url = None
            uow.products.add(product)

    # Método para subir imagen de una categoría a cloudinary y actualizar el campo image_url
    def upload_category_image(
        self, category_id: int, file: UploadFile
    ) -> UploadResponse:
        self._validate_image_type(file)

        with CategoryUnitOfWork(self._session) as uow:
            category = uow.categories.get_by_id(category_id)

            if not category:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail=f"Categoría con id {category_id} no encontrada",
                )

            if category.image_url:
                old_public_id = self._get_public_id(category.image_url)

                if old_public_id:
                    self._delete_from_cloudinary(old_public_id)

            result = self._execute_upload(
                file,
                folder_suffix="categories",
                public_id=str(category_id),
            )

            category.image_url = result.url
            uow.categories.add(category)

        return result

    # Método para eliminar la imagen de una categoría de cloudinary y limpiar el campo image_url
    def delete_category_image(self, category_id: int) -> None:
        with CategoryUnitOfWork(self._session) as uow:
            category = uow.categories.get_by_id(category_id)
            if not category:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail=f"Categoría con id {category_id} no encontrada",
                )

            if not category.image_url:
                return HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="La categoría no tiene ninguna imagen asociada para eliminar",
                )

            public_id = self._get_public_id(category.image_url)
            if public_id:
                self._delete_from_cloudinary(public_id)

            category.image_url = None
            uow.categories.add(category)
