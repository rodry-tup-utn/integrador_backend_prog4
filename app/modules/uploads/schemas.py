from sqlmodel import SQLModel


class UploadResponse(SQLModel):
    url: str
    public_id: str
