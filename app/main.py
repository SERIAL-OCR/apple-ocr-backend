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
def health() -> dict[str, str]:
    return {"status": "ok"}


# Routers
app.include_router(serials_router)
