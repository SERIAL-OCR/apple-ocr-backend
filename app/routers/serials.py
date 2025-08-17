from datetime import datetime, timedelta, timezone
import os
import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, File, HTTPException, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

# Configure logging
logger = logging.getLogger(__name__)

from fastapi.responses import FileResponse

from app.services.export import generate_excel
from app.pipeline.ocr_adapter_improved import progressive_process
from app.db import insert_serial
from app.services.eval import evaluate_dataset
from app.config import DEVICE_PRESETS, get_device_preset, get_config
from app.services.param_cache import get_best_params, list_cached_presets, schedule_param_sweep, is_sweep_running

router = APIRouter()

# In-memory job storage 
job_store: Dict[str, Dict[str, Any]] = {}

# Background task queue
task_queue: List[str] = []

def _auto_select_preset(device_type: str = None) -> str:
    """Auto-select the best preset based on device type."""
    if not device_type:
        return "etched"  # Default fallback
    
    device_type_lower = device_type.lower()
    
    # Check for exact matches first
    if device_type_lower in DEVICE_PRESETS:
        return DEVICE_PRESETS[device_type_lower]["preset"]
    
    # Check for partial matches
    for key, device_info in DEVICE_PRESETS.items():
        if key in device_type_lower or device_type_lower in key:
            return device_info["preset"]
    
    # Default to etched for Mac devices, screen for iOS devices
    if any(mac_key in device_type_lower for mac_key in ["mac", "imac", "macmini"]):
        return "etched"
    elif any(ios_key in device_type_lower for ios_key in ["iphone", "ipad"]):
        return "screen"
    else:
        return "etched"  # Default fallback

@router.post("/scan")
async def submit_scan(
    image: UploadFile = File(...),
    device_type: Optional[str] = None,
    preset: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
) -> dict:
    """Submit a scan for asynchronous processing.
    
    Returns immediately with a job ID for tracking.
    """
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Read image data before starting background task (UploadFile gets closed after request)
    image_data = await image.read()
    
    # Store job metadata
    job_store[job_id] = {
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "device_type": device_type,
        "preset": preset,
        "image_filename": image.filename,
        "progress": 0,
        "message": "Scan submitted successfully"
    }
    
    # Add to background task queue
    task_queue.append(job_id)
    
    # Start background processing with image data
    if background_tasks:
        background_tasks.add_task(process_scan_background, job_id, image_data, device_type)
    
    logger.info(f"Scan submitted with job ID: {job_id}")
    
    return {
        "job_id": job_id,
        "status": "submitted",
        "message": "Scan received and queued for processing",
        "estimated_time": "15-25 seconds",  # Updated for optimized pipeline
        "check_status_url": f"/result/{job_id}"
    }

@router.get("/result/{job_id}")
async def get_scan_result(job_id: str) -> dict:
    """Get the status and results of a scan job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    # Clean up old completed jobs (older than 1 hour)
    if job["status"] in ["completed", "failed"] and \
               datetime.now() - datetime.fromisoformat(job["created_at"]) > timedelta(hours=1):
        del job_store[job_id]
        raise HTTPException(status_code=404, detail="Job expired")
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "created_at": job["created_at"], 
        "updated_at": job.get("updated_at", job["created_at"]), 
        "results": job.get("results"),
        "error": job.get("error")
    }

async def process_scan_background(job_id: str, image_data: bytes, device_type: str = None):
    """Background task for processing OCR scan with hybrid fallback strategy"""
    try:
        # Update job status to processing
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = 10
        job_store[job_id]["message"] = "Starting OCR processing..."
        job_store[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Auto-select preset based on device type
        preset = _auto_select_preset(device_type)
        job_store[job_id]["preset"] = preset
        
        # Update progress
        job_store[job_id]["progress"] = 20
        job_store[job_id]["message"] = f"Using preset: {preset}"
        job_store[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Determine fallback strategy based on production mode
        if get_config("PRODUCTION_MODE", False):
            use_tesseract_fallback = get_config("ENABLE_TESSERACT_FALLBACK", True)
            max_processing_time = get_config("MAX_PROCESSING_TIME", 35.0)
            early_stop_confidence = get_config("EARLY_STOP_CONFIDENCE", 0.75)
            logger.info(f"[Production] Using fallback strategy: {get_config('FALLBACK_STRATEGY', 'hybrid')}")
        else:
            # Development mode: optimized for detection
            use_tesseract_fallback = True  # Enable Tesseract fallback
            max_processing_time = 30.0
            early_stop_confidence = 0.5  # Lower threshold for better detection
            logger.info("[Development] Enhanced mode with full fallback")
        
        # Update progress
        job_store[job_id]["progress"] = 30
        job_store[job_id]["message"] = "Running progressive OCR pipeline..."
        job_store[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Run progressive processing with hybrid fallback
        results = progressive_process(
            image_bytes=image_data,
            min_confidence=0.6,
            early_stop_confidence=early_stop_confidence,
            max_processing_time=max_processing_time,
            use_tesseract_fallback=use_tesseract_fallback,
            use_yolo_roi=get_config("USE_YOLO_ROI", True),
            try_invert=get_config("TRY_INVERT", True),
            try_multi_scale=get_config("TRY_MULTI_SCALE", False),
            device_type=device_type,
            production_mode=get_config("PRODUCTION_MODE", False),
            fallback_strategy=get_config("FALLBACK_STRATEGY", "hybrid")
        )
        
        # Update progress
        job_store[job_id]["progress"] = 90
        job_store[job_id]["message"] = "Processing completed, finalizing results..."
        job_store[job_id]["updated_at"] = datetime.now().isoformat()
        
        if results and len(results) > 0:
            # Success: Extract top results
            top_results = []
            for result in results[:5]:  # Top 5 results
                top_results.append({
                    "serial": result.serial,
                    "confidence": result.confidence,
                    "method": getattr(result, 'method', 'easyocr'),
                    "roi_index": getattr(result, 'roi_index', None)
                })
            
            # Find top result
            top_result = max(results, key=lambda x: x.confidence)
            
            job_store[job_id]["status"] = "completed"
            job_store[job_id]["progress"] = 100
            job_store[job_id]["message"] = f"Successfully detected {len(results)} serial numbers"
            job_store[job_id]["results"] = {
                "serials": top_results,
                "top_result": {
                    "serial": top_result.serial,
                    "confidence": top_result.confidence
                },
                "total_detected": len(results),
                "processing_time": (datetime.now() - datetime.fromisoformat(job_store[job_id]["created_at"])).total_seconds(),
                "fallback_used": any(getattr(r, 'method', 'easyocr') == 'tesseract' for r in results),
                "strategy_used": get_config("FALLBACK_STRATEGY", "hybrid")
            }
            job_store[job_id]["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Job {job_id} completed successfully with {len(results)} results")
            
        else:
            # No results found - this should not happen with proper fallback
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["progress"] = 100
            job_store[job_id]["message"] = "No serial numbers detected after all fallback attempts"
            job_store[job_id]["error"] = "OCR pipeline failed to detect any serial numbers"
            job_store[job_id]["updated_at"] = datetime.now().isoformat()
            
            logger.warning(f"Job {job_id} failed: No results found even with fallback")
            
    except Exception as e:
        # Handle any errors during processing
        error_msg = f"Processing failed: {str(e)}"
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Processing failed due to an error"
        job_store[job_id]["error"] = error_msg
        job_store[job_id]["updated_at"] = datetime.now().isoformat()
        
        logger.error(f"Job {job_id} failed: {error_msg}")
        
        # If this is production and we have a critical failure, log it for monitoring
        if get_config("PRODUCTION_MODE", False):
            logger.critical(f"PRODUCTION CRITICAL: Job {job_id} failed in production mode: {error_msg}")

@router.get("/jobs")
async def list_jobs(limit: int = Query(10, ge=1, le=100)) -> dict:
    """List recent scan jobs (for debugging/admin)."""
    recent_jobs = []
    for job_id, job in list(job_store.items())[-limit:]:
        recent_jobs.append({
            "job_id": job_id,
            "status": job["status"],
            "created_at": job["created_at"],
            "device_type": job["device_type"],
            "preset": job["preset"]
        })
    
    return {
        "total_jobs": len(job_store),
        "recent_jobs": recent_jobs
    }

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    """Delete a scan job (for cleanup)."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del job_store[job_id]
    return {"message": f"Job {job_id} deleted successfully"}


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
    upscale_scale: float = Query(3.0),  # Changed from 4.0 to 3.0 based on test results
    mode: str = Query("gray", pattern="^(binary|gray)$"),  # Changed default to gray
    # OCR tunables
    low_text: float = Query(0.3),  # Changed from 0.2 to 0.3 based on test results
    text_threshold: float = Query(0.3),  # Changed from 0.4 to 0.3 based on test results
    # ROI detection
    roi: bool = Query(True),  # Enabled by default for better accuracy
    roi_top_k: int = Query(3),  # Increased from 2 to 3
    roi_pad: int = Query(10),  # Slightly increased padding
    adaptive_pad: bool = Query(True),  # Use adaptive padding
    # Glare reduction
    glare_reduction: Optional[str] = Query("adaptive", pattern="^(tophat|division|adaptive|multi)$"),  # Changed from None to "adaptive"
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
    # Progressive processing options
    use_progressive: bool = Query(True, description="Use progressive processing pipeline for better accuracy"),
    early_stop_confidence: float = Query(0.95, ge=0.0, le=1.0, description="Confidence threshold for early stopping"),
    max_processing_time: float = Query(30.0, ge=1.0, le=120.0, description="Maximum processing time in seconds"),
    use_yolo_roi: bool = Query(True, description="Use YOLO model for ROI detection"),
    use_tesseract_fallback: bool = Query(True, description="Use Tesseract as fallback if EasyOCR fails"),
) -> dict:
    """Process an image to extract serial numbers."""
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    data = await image.read()
    debug_path = None
    if debug_save:
        os.makedirs("exports/debug", exist_ok=True)
        debug_path = os.path.join(
            "exports", "debug", f"preproc_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.png"
        )
    
    # Apply preset if specified or auto-select based on device_type
    extract_params = {}
    
    # If no preset is specified but device_type is provided, auto-select preset
    if not preset and device_type:
        auto_preset = get_device_preset(device_type)
        logger.info(f"Auto-selected preset '{auto_preset}' for device type '{device_type}'")
        preset = auto_preset
    
    if preset:
        # First check if we have cached optimal parameters for this preset
        cached_params = get_best_params(preset)
        
        # If no cache, fall back to default preset config
        preset_config = cached_params if cached_params else DEVICE_PRESETS.get(preset, {})
        
        if preset_config:
            # Use preset parameters as base
            extract_params = preset_config.copy()
            
            # Log the preset being used
            logger.info(f"Using preset '{preset}' with {len(extract_params)} parameters")
    
    # Add explicitly set parameters (overriding preset values)
    # Only add non-default values to avoid overriding preset values unnecessarily
    if clip_limit != 2.0:
        extract_params["clip_limit"] = clip_limit
    if bilateral_d != 7:
        extract_params["bilateral_d"] = bilateral_d
    if bilateral_sigma_color != 75:
        extract_params["bilateral_sigma_color"] = bilateral_sigma_color
    if bilateral_sigma_space != 75:
        extract_params["bilateral_sigma_space"] = bilateral_sigma_space
    if thresh_block_size != 35:
        extract_params["thresh_block_size"] = thresh_block_size
    if thresh_C != 11:
        extract_params["thresh_C"] = thresh_C
    if morph_kernel != 2:
        extract_params["morph_kernel"] = morph_kernel
    if upscale_scale != 3.0:
        extract_params["upscale_scale"] = upscale_scale
    if mode != "gray":
        extract_params["mode"] = mode
    if low_text != 0.3:
        extract_params["low_text"] = low_text
    if text_threshold != 0.3:
        extract_params["text_threshold"] = text_threshold
    if roi != True:
        extract_params["roi"] = roi
    if roi_top_k != 3:
        extract_params["roi_top_k"] = roi_top_k
    if roi_pad != 10:
        extract_params["roi_pad"] = roi_pad
    if adaptive_pad != True:
        extract_params["adaptive_pad"] = adaptive_pad
    if glare_reduction != "adaptive":
        extract_params["glare_reduction"] = glare_reduction
    if mag_ratio != 1.2:
        extract_params["mag_ratio"] = mag_ratio
    if fine_rotation != False:
        extract_params["fine_rotation"] = fine_rotation
    if zoom_strips != 0:
        extract_params["zoom_strips"] = zoom_strips
    if keyword_crop != False:
        extract_params["keyword_crop"] = keyword_crop

    # Parse rotations if provided
    if rotations:
        try:
            rotation_angles = tuple(int(a.strip()) for a in rotations.split(",") if a.strip())
            extract_params["try_rotations"] = rotation_angles
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'rotations' format; expected numbers like '0,180'")

    try:
        # Use progressive processing if enabled (default: True)
        if use_progressive:
            serials = progressive_process(
                data,
                min_confidence=min_confidence,
                early_stop_confidence=early_stop_confidence,
                debug_save_path=debug_path,
                max_processing_time=max_processing_time,
                use_tesseract_fallback=use_tesseract_fallback,
                use_yolo_roi=use_yolo_roi,
                debug_steps=debug_save,
                **extract_params
            )
        else:
            # Fall back to direct processing if progressive is disabled
            serials = extract_serials(
                data,
                min_confidence=min_confidence,
                debug_save_path=debug_path,
                **extract_params
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
                f"no_detection_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.png"
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
                    **extract_params
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


@router.post("/process-progressive")
async def process_progressive(
    image: UploadFile = File(...),
    device_type: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    early_stop_confidence: float = Query(0.95, ge=0.0, le=1.0),
    max_processing_time: float = Query(15.0, ge=1.0, le=120.0),
    debug_save: Optional[bool] = Query(False),
    persist: bool = Query(True),
    # Preset selection
    preset: Optional[str] = Query(None, description="Use preset: default, etched, printed, apple_silicon"),
    # YOLO ROI detection
    use_yolo_roi: bool = Query(True, description="Use YOLO model for ROI detection"),
    # Tesseract fallback
    use_tesseract_fallback: bool = Query(True, description="Use Tesseract as fallback if EasyOCR fails"),
) -> dict:
    """Process an image to extract serial numbers using the progressive pipeline.
    
    This endpoint uses a multi-stage processing approach that starts with fast methods
    and only uses more complex (and slower) methods if needed.
    """
    if image.content_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    data = await image.read()
    debug_path = None
    if debug_save:
        os.makedirs("exports/debug", exist_ok=True)
        debug_path = os.path.join(
            "exports", "debug", f"progressive_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.png"
        )
    
    # Apply preset if specified
    extract_params = {}
    if preset:
        # First check if we have cached optimal parameters for this preset
        cached_params = get_best_params(preset)
        
        # If no cache, fall back to default preset config
        preset_config = cached_params if cached_params else DEVICE_PRESETS.get(preset, {})
        
        if preset_config:
            # Use preset parameters
            extract_params = preset_config

    try:
        serials = progressive_process(
            data,
            min_confidence=min_confidence,
            early_stop_confidence=early_stop_confidence,
            debug_save_path=debug_path,
            max_processing_time=max_processing_time,
            use_tesseract_fallback=use_tesseract_fallback,
            use_yolo_roi=use_yolo_roi,
            debug_steps=debug_save,
            **extract_params
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
                f"no_detection_progressive_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.png"
            )
            # Save original image for failed detections
            with open(failed_path, 'wb') as f:
                f.write(data)
            
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
    export_name = f"exports/serials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
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
