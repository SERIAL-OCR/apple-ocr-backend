from datetime import datetime
import os
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.export import generate_excel
from app.pipeline.ocr_adapter import extract_serials
from app.db import insert_serial

router = APIRouter()


@router.post("/process-serial")
async def process_serial(image: UploadFile = File(...), device_type: Optional[str] = None) -> dict:
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    data = await image.read()
    try:
        serials = extract_serials(data)
    except Exception as exc:  # noqa: BLE001 MVP simplicity
        raise HTTPException(status_code=400, detail=f"Failed to process image: {exc}") from exc

    if not serials:
        return {"serials": []}

    # Persist top result and return all
    top_serial, top_conf = max(serials, key=lambda x: x[1])
    insert_serial(top_serial, device_type=device_type, confidence=top_conf)

    return {
        "serials": [
            {"serial": s, "confidence": c} for s, c in sorted(serials, key=lambda x: x[1], reverse=True)
        ],
        "saved": {"serial": top_serial, "confidence": top_conf},
    }


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
