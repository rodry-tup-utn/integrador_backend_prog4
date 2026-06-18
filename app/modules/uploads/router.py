from fastapi import APIRouter, Depends, Path, UploadFile, File, status
from sqlmodel import Session
from typing import Annotated

from app.modules.uploads.schemas import UploadResponse
from app.modules.uploads.service import UploadService
from app.core.database import get_session
from app.modules.auth.dependencies import require_role


def get_upload_service(session: Session = Depends(get_session)) -> UploadService:
    return UploadService(session)


router = APIRouter(
    prefix="/upload",
    tags=["Admin - Upload"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)


@router.post(
    "/product/{id}", response_model=UploadResponse, status_code=status.HTTP_200_OK
)
def upload_product_image(
    id: Annotated[int, Path(ge=1)],
    file: UploadFile = File(...),
    svc: UploadService = Depends(get_upload_service),
):
    return svc.upload_product_image(id, file)


@router.delete(
    "/product/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_image(
    id: Annotated[int, Path(ge=1)], svc: UploadService = Depends(get_upload_service)
):
    svc.delete_product_image(id)


@router.post(
    "/category/{id}", response_model=UploadResponse, status_code=status.HTTP_200_OK
)
def upload_category_image(
    id: Annotated[int, Path(ge=1)],
    file: UploadFile = File(...),
    svc: UploadService = Depends(get_upload_service),
):
    return svc.upload_category_image(id, file)


@router.delete("/category/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_image(
    id: Annotated[int, Path(ge=1)], svc: UploadService = Depends(get_upload_service)
):
    svc.delete_category_image(id)
