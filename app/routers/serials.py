from datetime import datetime, timedelta, timezone
import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

from fastapi.responses import FileResponse

from app.services.export import generate_excel
from app.db import insert_serial
from app.config import get_config
from app.utils.validation import is_valid_apple_serial, validate_apple_serial_extended

router = APIRouter()

# Security
security = HTTPBearer(auto_error=False)

# Phase 2.1: On-device OCR data models
class SerialSubmission(BaseModel):
    """Data contract for POST /serials endpoint (Phase 2.1)"""
    serial: str = Field(..., min_length=12, max_length=12, description="12-character Apple serial number")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score (0.0-1.0)")
    device_type: Optional[str] = Field(None, description="Type of Apple device (e.g., 'iPhone', 'MacBook')")
    source: str = Field(..., pattern="^(ios|mac)$", description="Source platform: 'ios' or 'mac'")
    ts: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp of scan")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes or metadata")
    
    @validator('serial')
    def validate_serial(cls, v):
        """Validate Apple serial number format and content"""
        if not is_valid_apple_serial(v):
            raise ValueError(f"Invalid Apple serial number format: {v}")
        return v.upper()
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is within valid range"""
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

class SerialResponse(BaseModel):
    """Response model for POST /serials endpoint"""
    success: bool
    serial_id: Optional[str] = None
    message: str
    validation_passed: bool
    confidence_acceptable: bool
    timestamp: datetime = Field(default_factory=datetime.now)

# API key validation (Phase 2.1 security)
def validate_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Validate API key for on-device OCR submissions"""
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    
    # For Phase 2.1 pilot, use a simple static key
    # TODO: Implement proper key management for production
    valid_keys = get_config("VALID_API_KEYS", ["phase2-pilot-key-2024"]).split(",")
    
    if credentials.credentials not in valid_keys:
        logger.warning(f"Invalid API key attempt: {credentials.credentials[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return credentials.credentials

# Phase 2.1: On-device OCR endpoint
@router.post("/serials", response_model=SerialResponse)
async def submit_serial_result(
    submission: SerialSubmission,
    api_key: str = Depends(validate_api_key)
) -> SerialResponse:
    """
    Submit validated serial number result from on-device OCR (Phase 2.1).
    
    This endpoint accepts serial numbers that have been validated client-side
    using Vision/VisionKit on iOS/macOS devices. No image uploads required.
    """
    start_time = datetime.now()
    
    try:
        # Log submission for observability
        logger.info(
            f"Serial submission: {submission.serial[:4]}***{submission.serial[-4:]} "
            f"(conf={submission.confidence:.3f}, source={submission.source}, "
            f"device={submission.device_type or 'unknown'})"
        )
        
        # Additional server-side validation
        validation_passed, validation_reason = validate_apple_serial_extended(submission.serial)
        
        # Confidence threshold check
        min_confidence = get_config("MIN_ACCEPTANCE_CONFIDENCE", 0.65)
        confidence_acceptable = submission.confidence >= min_confidence
        
        # Determine if we should accept this submission
        should_accept = validation_passed and confidence_acceptable
        
        if should_accept:
            # Store in database
            serial_id = insert_serial(
                serial=submission.serial,
                device_type=submission.device_type,
                confidence=submission.confidence,
                source=submission.source,
                notes=submission.notes,
                validation_passed=validation_passed,
                confidence_acceptable=confidence_acceptable
            )
            
            # Log successful storage
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Serial stored successfully: ID={serial_id}, "
                f"serial={submission.serial[:4]}***{submission.serial[-4:]}, "
                f"processing_time={processing_time:.1f}ms"
            )
            
            return SerialResponse(
                success=True,
                serial_id=str(serial_id),
                message="Serial number stored successfully",
                validation_passed=validation_passed,
                confidence_acceptable=confidence_acceptable
            )
        else:
            # Log rejection
            rejection_reason = []
            if not validation_passed:
                rejection_reason.append("validation_failed")
            if not confidence_acceptable:
                rejection_reason.append(f"low_confidence_{submission.confidence:.3f}")
            
            logger.warning(
                f"Serial submission rejected: {submission.serial[:4]}***{submission.serial[-4:]} "
                f"reasons={rejection_reason}"
            )
            
            return SerialResponse(
                success=False,
                message=f"Serial rejected: {', '.join(rejection_reason)}",
                validation_passed=validation_passed,
                confidence_acceptable=confidence_acceptable
            )
            
    except Exception as e:
        logger.error(f"Error processing serial submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/history")
async def get_scan_history(
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    source: Optional[str] = Query(None, description="Filter by source (ios/mac/server)"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    validation_status: Optional[str] = Query(None, description="Filter by validation status (valid/invalid)"),
    search: Optional[str] = Query(None, description="Search by serial number"),
    sort_by: str = Query("timestamp", description="Sort field (timestamp, confidence, serial)"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
) -> dict:
    """Get scan history with enhanced filtering, pagination, and sorting."""
    from app.db import fetch_serials, get_serial_stats
    
    try:
        # Validate parameters
        if source and source not in ["ios", "mac", "server"]:
            raise HTTPException(status_code=400, detail="Invalid source. Must be ios, mac, or server")
        
        if validation_status and validation_status not in ["valid", "invalid"]:
            raise HTTPException(status_code=400, detail="Invalid validation_status. Must be valid or invalid")
        
        if sort_by not in ["timestamp", "confidence", "serial"]:
            raise HTTPException(status_code=400, detail="Invalid sort_by. Must be timestamp, confidence, or serial")
        
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(status_code=400, detail="Invalid sort_order. Must be asc or desc")
        
        # Get all scans from database with Phase 2.1 fields
        db_results = fetch_serials()
        
        # Apply filters
        filtered_results = []
        for row in db_results:
            if len(row) >= 9:
                id, created_at, serial, device_type_val, confidence, source_val, notes, validation_passed, confidence_acceptable = row[:9]
                
                # Apply source filter
                if source and source_val != source:
                    continue
                
                # Apply device type filter
                if device_type and device_type_val != device_type:
                    continue
                
                # Apply validation status filter
                if validation_status:
                    if validation_status == "valid" and not validation_passed:
                        continue
                    if validation_status == "invalid" and validation_passed:
                        continue
                
                # Apply search filter
                if search and search.lower() not in serial.lower():
                    continue
                
                filtered_results.append(row)
            else:
                # Handle legacy rows
                filtered_results.append(row)
        
        # Apply sorting
        if sort_by == "timestamp":
            filtered_results.sort(key=lambda x: x[1], reverse=(sort_order == "desc"))
        elif sort_by == "confidence":
            filtered_results.sort(key=lambda x: x[4] or 0, reverse=(sort_order == "desc"))
        elif sort_by == "serial":
            filtered_results.sort(key=lambda x: x[2], reverse=(sort_order == "desc"))
        
        # Apply pagination
        total_count = len(filtered_results)
        paginated_results = filtered_results[offset:offset + limit]
        
        # Convert to iOS-friendly format with enhanced data
        history = []
        for row in paginated_results:
            if len(row) >= 9:
                id, created_at, serial, device_type_val, confidence, source_val, notes, validation_passed, confidence_acceptable = row[:9]
                history.append({
                    "id": id,
                    "timestamp": created_at,
                    "serial": serial,
                    "device_type": device_type_val or "unknown",
                    "confidence": confidence or 0.0,
                    "source": source_val or "server",
                    "notes": notes,
                    "validation_passed": bool(validation_passed),
                    "confidence_acceptable": bool(confidence_acceptable),
                    "status": "completed" if validation_passed and confidence_acceptable else "rejected"
                })
            else:
                # Handle legacy rows
                id, created_at, serial, device_type_val, confidence = row[:5]
            history.append({
                "id": id,
                "timestamp": created_at,
                "serial": serial,
                    "device_type": device_type_val or "unknown",
                "confidence": confidence or 0.0,
                    "source": "server",  # Default for legacy
                    "notes": None,
                    "validation_passed": True,  # Default for legacy
                    "confidence_acceptable": True,  # Default for legacy
                "status": "completed"
            })
        
        # Get statistics for dashboard
        stats = get_serial_stats()
        
        return {
            "total_scans": total_count,
            "filtered_scans": len(paginated_results),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
                "total_pages": (total_count + limit - 1) // limit,
                "current_page": (offset // limit) + 1
            },
            "filters": {
                "source": source,
                "device_type": device_type,
                "validation_status": validation_status,
                "search": search
            },
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            },
            "recent_scans": history,
            "statistics": stats,
            "export_url": "/export"
        }
    except HTTPException:
        # Re-raise HTTPExceptions without wrapping them
        raise
    except Exception as e:
        logger.error(f"Failed to fetch scan history: {e}")
        return {
            "total_scans": 0,
            "filtered_scans": 0,
            "pagination": {},
            "filters": {},
            "sorting": {},
            "recent_scans": [],
            "statistics": {},
            "export_url": "/export",
            "error": "Failed to fetch history"
        }

@router.get("/stats")
async def get_system_stats() -> dict:
    """Get Phase 2.1 system statistics and observability data."""
    from app.db import get_serial_stats
    
    try:
        # Get database statistics
        db_stats = get_serial_stats()
        
        # Get system health metrics
        system_health = {
            "uptime": "TODO",  # TODO: Add uptime tracking
            "last_activity": datetime.now().isoformat()
        }
        
        return {
            "database": db_stats,
            "system": system_health,
            "phase": "2.1",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/health")
async def health_check() -> dict:
    """Enhanced health check for Phase 2.1 with observability."""
    from app.db import get_connection
    
    try:
        # Check database connectivity
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        
        # Get basic stats
        from app.db import get_serial_stats
        stats = get_serial_stats()
        
        return {
            "status": "healthy",
            "phase": "2.1",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "total_serials": stats["total_serials"],
            "recent_activity": {
                "ios_submissions": stats["by_source"]["ios"],
                "mac_submissions": stats["by_source"]["mac"],
                "server_submissions": stats["by_source"]["server"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/export")
def export_excel(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    source: Optional[str] = Query(None, description="Filter by source (ios/mac/server)"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    validation_status: Optional[str] = Query(None, description="Filter by validation status (valid/invalid)")
) -> FileResponse:
    """Export serial numbers to Excel file with enhanced filtering and formatting."""
    
    try:
        # Parse date filters
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            try:
                parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
        
        if date_to:
            try:
                parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d")
                # Set to end of day
                parsed_date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Validate source filter
        if source and source not in ["ios", "mac", "server"]:
            raise HTTPException(status_code=400, detail="Invalid source. Must be ios, mac, or server")
        
        # Validate validation status filter
        if validation_status and validation_status not in ["valid", "invalid"]:
            raise HTTPException(status_code=400, detail="Invalid validation_status. Must be valid or invalid")
        
        # Generate Excel file with filters
        export_name = f"storage/exports/serials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        generate_excel(
            export_name,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            source=source,
            device_type=device_type,
            validation_status=validation_status
        )
        
        # Create filename with filter info
        filename_parts = ["apple_serials", datetime.now().strftime('%Y%m%d_%H%M%S')]
        if source:
            filename_parts.append(f"source_{source}")
        if device_type:
            filename_parts.append(f"device_{device_type}")
        if validation_status:
            filename_parts.append(f"validation_{validation_status}")
        
        filename = f"{'_'.join(filename_parts)}.xlsx"
        
        return FileResponse(
            export_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    except HTTPException:
        # Re-raise HTTPExceptions without wrapping them
        raise
    except Exception as e:
        logger.error(f"Failed to export Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")

@router.get("/config")
async def get_client_config() -> dict:
    """Get Phase 2.1 configuration for client consumption."""
    from app.config import get_phase2_config
    
    return get_phase2_config()
