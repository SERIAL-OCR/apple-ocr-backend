from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import initialize_storage
from app.routers.serials import router as serials_router

app = FastAPI(title="Apple Serial OCR Backend", version="0.1.0")

# MVP: allow all origins; restrict later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
