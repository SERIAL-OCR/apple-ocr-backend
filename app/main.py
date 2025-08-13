import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import initialize_storage
from app.routers.serials import router as serials_router
from app.utils.logging import log_api_request

app = FastAPI(title="Apple Serial OCR Backend", version="0.1.0")

# MVP: allow all origins; restrict later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Process the request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Extract query parameters
        query_params = {}
        for key, value in request.query_params.items():
            query_params[key] = value
        
        # Log the request
        log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            params=query_params,
            status_code=response.status_code,
            response_time=response_time,
            client_ip=client_ip,
        )
        
        return response


app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    initialize_storage()


@app.get("/health")
def health() -> dict:
    gpu_info = {
        "torch_present": False,
        "cuda_available": False,
        "cuda_version": None,
        "device_count": 0,
        "use_gpu_config": False,
    }
    try:
        import torch  # type: ignore
        from app.config import OCR_SETTINGS

        gpu_info["torch_present"] = True
        gpu_info["cuda_available"] = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        gpu_info["cuda_version"] = getattr(getattr(torch, "version", None), "cuda", None)
        gpu_info["device_count"] = torch.cuda.device_count() if gpu_info["cuda_available"] else 0
        gpu_info["use_gpu_config"] = bool(OCR_SETTINGS.get("use_gpu"))
    except Exception:
        pass

    return {"status": "ok", "gpu": gpu_info}


# Routers
app.include_router(serials_router)
