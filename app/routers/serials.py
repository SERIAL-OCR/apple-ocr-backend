from datetime import datetime
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.export import generate_excel

router = APIRouter()


@router.post("/process-serial")
async def process_serial(image: UploadFile = File(...)) -> dict:
    # Placeholder: OCR integration (EasyOCR) to be implemented
    # Accept the file to validate upload path works
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    # Not implemented yet
    raise HTTPException(status_code=501, detail="OCR processing not implemented yet")


@router.get("/export")
def export_excel() -> FileResponse:
    export_name = f"exports/serials_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = generate_excel(export_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Failed to generate export")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path),
    )
