from typing import Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    filename: str
    content_type: Optional[str]
    saved_path: str
    size: int