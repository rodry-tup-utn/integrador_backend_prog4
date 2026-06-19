from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlmodel import Session

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


# ── Standalone ────────────────────────────────────────────────

@router.post("", response_model=UploadResponse, status_code=status.HTTP_200_OK)
def upload_image(
    file: UploadFile = File(...),
    svc: UploadService = Depends(get_upload_service),
):
    return svc.upload_image(file)


@router.delete("/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    public_id: str,
    svc: UploadService = Depends(get_upload_service),
):
    svc.delete_image(public_id)


