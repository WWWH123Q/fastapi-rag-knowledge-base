from app.schemas.file_schema import FileUploadResponse
from fastapi import APIRouter, UploadFile, File
from app.services.file_service import save_upload_file

router = APIRouter()
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    result = await save_upload_file(file)

    return FileUploadResponse(**result)