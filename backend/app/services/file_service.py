from pathlib import Path

from fastapi import UploadFile, HTTPException


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 只允许这些文件后缀
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".md"}


async def save_upload_file(file: UploadFile) -> dict:
    # 1. 取出文件后缀，比如 .pdf / .docx
    suffix = Path(file.filename).suffix.lower()

    # 2. 判断文件后缀是否允许
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{suffix}，只允许上传 txt/pdf/docx/md 文件"
        )

    # 3. 拼接保存路径
    file_path = UPLOAD_DIR / file.filename

    # 4. 读取文件内容
    content = await file.read()

    # 5. 保存到本地
    with open(file_path, "wb") as f:
        f.write(content)

    # 6. 返回文件信息
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "saved_path": str(file_path),
        "size": len(content)
    }