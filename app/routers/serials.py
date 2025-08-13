from datetime import datetime
import os
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse

from app.services.export import generate_excel
from app.pipeline.ocr_adapter import extract_serials
from app.db import insert_serial
from app.services.eval import evaluate_dataset
from app.config import DEVICE_PRESETS
from app.services.param_cache import (
    get_best_params, list_cached_presets, schedule_param_sweep, is_sweep_running
)

router = APIRouter()


@router.post("/process-serial")
async def process_serial(
    image: UploadFile = File(...),
    device_type: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    debug_save: Optional[bool] = Query(False),
    persist: bool = Query(True),
    # Preset selection
    preset: Optional[str] = Query(None, description="Use preset: etched, sticker, screen"),
    # Preprocessing tunables
    clip_limit: float = Query(2.0),
    tile_grid: int = Query(8),
    bilateral_d: int = Query(7),
    bilateral_sigma_color: int = Query(75),
    bilateral_sigma_space: int = Query(75),
    thresh_block_size: int = Query(35),
    thresh_C: int = Query(11),
    morph_kernel: int = Query(2),
    upscale_scale: float = Query(4.0),  # Increased from 2.0 for better accuracy
    mode: str = Query("gray", pattern="^(binary|gray)$"),  # Changed default to gray
    # OCR tunables
    low_text: float = Query(0.2),  # Tuned for better detection
    text_threshold: float = Query(0.4),  # Tuned for better detection
    # ROI detection
    roi: bool = Query(True),  # Enabled by default for better accuracy
    roi_top_k: int = Query(3),  # Increased from 2 to 3
    roi_pad: int = Query(10),  # Slightly increased padding
    adaptive_pad: bool = Query(True),  # Use adaptive padding
    # Glare reduction
    glare_reduction: Optional[str] = Query(None, pattern="^(tophat|division|adaptive)$"),
    # EasyOCR magnification ratio
    mag_ratio: float = Query(1.2),  # Slightly higher magnification
    # Fast/slow angle control
    rotations: Optional[str] = Query(
        None,
        description="Comma-separated angles to try (e.g., '0,180' or '0,90,180,270')",
    ),
    # Fine-grained rotation and zoom controls
    fine_rotation: bool = Query(False, description="Enable fine-grained rotations (±15°, ±30° around base angles)"),
    zoom_strips: int = Query(0, ge=0, le=10, description="Split image into N horizontal strips to zoom (0=off)"),
    keyword_crop: bool = Query(False, description="Crop near 'Serial' keyword to focus on serial block"),
) -> dict:
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    data = await image.read()
    debug_path = None
    if debug_save:
        os.makedirs("exports/debug", exist_ok=True)
        debug_path = os.path.join(
            "exports", "debug", f"preproc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')}.png"
        )
    
    # Apply preset if specified
    if preset:
        # First check if we have cached optimal parameters for this preset
        cached_params = get_best_params(preset)
        
        # If no cache, fall back to default preset config
        preset_config = cached_params if cached_params else DEVICE_PRESETS.get(preset, {})
        
        if preset_config:
            # Override parameters with preset values (only if not explicitly set by user)
            # We check if the value equals the default to determine if user set it
            if clip_limit == 2.0:
                clip_limit = preset_config.get("clip_limit", clip_limit)
            if bilateral_d == 7:
                bilateral_d = preset_config.get("bilateral_d", bilateral_d)
            if thresh_block_size == 35:
                thresh_block_size = preset_config.get("thresh_block_size", thresh_block_size)
            if thresh_C == 11:
                thresh_C = preset_config.get("thresh_C", thresh_C)
            if upscale_scale == 4.0:
                upscale_scale = preset_config.get("upscale_scale", upscale_scale)
            if mode == "gray":
                mode = preset_config.get("mode", mode)
            if low_text == 0.2:
                low_text = preset_config.get("low_text", low_text)
            if text_threshold == 0.4:
                text_threshold = preset_config.get("text_threshold", text_threshold)
            if roi == True:
                roi = preset_config.get("roi", roi)
            if roi_pad == 10:
                roi_pad = preset_config.get("roi_pad", roi_pad)
            if roi_top_k == 3:
                roi_top_k = preset_config.get("roi_top_k", roi_top_k)
            if adaptive_pad == True:
                adaptive_pad = preset_config.get("adaptive_pad", adaptive_pad)
            if glare_reduction is None:
                glare_reduction = preset_config.get("glare_reduction", glare_reduction)
            if mag_ratio == 1.2:
                mag_ratio = preset_config.get("mag_ratio", mag_ratio)

    # Parse rotations if provided
    rotation_angles = None
    if rotations:
        try:
            rotation_angles = tuple(int(a.strip()) for a in rotations.split(",") if a.strip())
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'rotations' format; expected numbers like '0,180'")

    try:
        serials = extract_serials(
            data,
            min_confidence=min_confidence,
            debug_save_path=debug_path,
            low_text=low_text,
            text_threshold=text_threshold,
            clip_limit=clip_limit,
            tile_grid=tile_grid,
            bilateral_d=bilateral_d,
            bilateral_sigma_color=bilateral_sigma_color,
            bilateral_sigma_space=bilateral_sigma_space,
            thresh_block_size=thresh_block_size,
            thresh_C=thresh_C,
            morph_kernel=morph_kernel,
            upscale_scale=upscale_scale,
            mode=mode,
            try_rotations=rotation_angles if rotation_angles else (0, 90, 180, 270),
            roi=roi,
            roi_top_k=roi_top_k,
            roi_pad=roi_pad,
            adaptive_pad=adaptive_pad,
            glare_reduction=glare_reduction,
            mag_ratio=mag_ratio,
            fine_rotation=fine_rotation,
            zoom_strips=zoom_strips,
            keyword_crop=keyword_crop,
        )
    except Exception as exc:  # noqa: BLE001 MVP simplicity
        raise HTTPException(status_code=400, detail=f"Failed to process image: {exc}") from exc

    if not serials:
        # Save failed detection for debugging
        failed_path = None
        if not debug_save:
            os.makedirs("exports/debug/failed", exist_ok=True)
            failed_path = os.path.join(
                "exports", "debug", "failed", 
                f"no_detection_{datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')}.png"
            )
            # Save original image for failed detections
            with open(failed_path, 'wb') as f:
                f.write(data)
            # Also save preprocessed version
            preproc_failed_path = failed_path.replace(".png", "_preprocessed.png")
            try:
                _ = extract_serials(
                    data, 
                    debug_save_path=preproc_failed_path,
                    clip_limit=clip_limit,
                    tile_grid=tile_grid,
                    bilateral_d=bilateral_d,
                    bilateral_sigma_color=bilateral_sigma_color,
                    bilateral_sigma_space=bilateral_sigma_space,
                    thresh_block_size=thresh_block_size,
                    thresh_C=thresh_C,
                    morph_kernel=morph_kernel,
                    upscale_scale=upscale_scale,
                    mode=mode,
                    roi=roi,
                    roi_top_k=roi_top_k,
                    roi_pad=roi_pad,
                    adaptive_pad=adaptive_pad,
                    glare_reduction=glare_reduction,
                    mag_ratio=mag_ratio,
                )
            except:
                pass
            
        return {"serials": [], "saved": None, "debug": debug_path, "persisted": False, 
                "failed_debug": failed_path}

    top_serial, top_conf = max(serials, key=lambda x: x[1])
    did_persist = False
    if persist:
        insert_serial(top_serial, device_type=device_type, confidence=top_conf)
        did_persist = True

    return {
        "serials": [
            {"serial": s, "confidence": c} for s, c in sorted(serials, key=lambda x: x[1], reverse=True)
        ],
        "saved": {"serial": top_serial, "confidence": top_conf} if did_persist else None,
        "debug": debug_path,
        "persisted": did_persist,
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


@router.get("/params")
def get_params(
    preset: Optional[str] = Query(None, description="Specific preset to get parameters for"),
) -> dict:
    """Get cached optimal parameters for presets."""
    if preset:
        params = get_best_params(preset)
        if not params:
            raise HTTPException(status_code=404, detail=f"No cached parameters found for preset: {preset}")
        return {"preset": preset, "params": params}
    
    # Return all cached presets
    return {"presets": list_cached_presets()}


@router.post("/params/sweep")
def trigger_param_sweep(
    preset: str = Query(..., description="Preset to optimize parameters for"),
    images_dir: str = Query("exported-assets", description="Directory containing test images"),
    labels_file: str = Query("exported-assets/labels.csv", description="CSV file with ground truth"),
) -> dict:
    """Trigger a parameter sweep to find optimal parameters for a preset."""
    # Check if a sweep is already running
    if is_sweep_running():
        raise HTTPException(status_code=409, detail="A parameter sweep is already running")
    
    # Schedule the sweep
    success = schedule_param_sweep(preset, images_dir, labels_file)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to schedule parameter sweep")
    
    return {
        "status": "scheduled",
        "preset": preset,
        "images_dir": images_dir,
        "labels_file": labels_file,
    }


@router.get("/evaluate")
def evaluate(
    dir: str = Query(..., description="Directory containing images and optional labels.csv"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    preset: Optional[str] = Query(None, description="Optional preset to apply for evaluation"),
    # Key processing knobs (subset to keep URL short)
    mode: str = Query("gray", pattern="^(binary|gray)$"),
    upscale_scale: float = Query(4.0),
    roi: bool = Query(True),
    roi_top_k: int = Query(3),
    roi_pad: int = Query(10),
    adaptive_pad: bool = Query(True),
    glare_reduction: Optional[str] = Query(None, pattern="^(tophat|division|adaptive)$"),
    low_text: float = Query(0.2),
    text_threshold: float = Query(0.4),
    mag_ratio: float = Query(1.2),
    fine_rotation: bool = Query(False),
    rotations: Optional[str] = Query(None),
    zoom_strips: int = Query(0, ge=0, le=10),
) -> dict:
    # Build params from query and optional preset
    params = {
        "mode": mode,
        "upscale_scale": upscale_scale,
        "roi": roi,
        "roi_top_k": roi_top_k,
        "roi_pad": roi_pad,
        "adaptive_pad": adaptive_pad,
        "glare_reduction": glare_reduction,
        "low_text": low_text,
        "text_threshold": text_threshold,
        "mag_ratio": mag_ratio,
        "fine_rotation": fine_rotation,
        "zoom_strips": zoom_strips,
    }
    if preset:
        # First check if we have cached optimal parameters for this preset
        cached_params = get_best_params(preset)
        
        # If no cache, fall back to default preset config
        preset_config = cached_params if cached_params else DEVICE_PRESETS.get(preset, {})
        
        if preset_config:
            params = {**params, **preset_config}

    # rotations are only used by /process, here we evaluate using default angles
    summary = evaluate_dataset(
        dir,
        min_confidence=min_confidence,
        extract_params=params,
    )
    return summary
