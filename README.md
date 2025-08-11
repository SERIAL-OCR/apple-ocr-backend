## Apple Serial Number OCR Backend (MVP)

Python 3.11 FastAPI backend for Apple serial number OCR MVP. Uses SQLite for storage and exports Excel reports. OCR pipeline integration (EasyOCR) will follow.

### Quickstart (local)

1. Create venv and install deps
```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Run server
```
uvicorn app.main:app --reload
```
Open `http://localhost:8000/docs` for API docs.

### Quickstart (Docker)
```
docker compose up --build
```
Service runs on `http://localhost:8000`.

### Endpoints
- GET `/health`: Service health check
- POST `/process-serial`: Upload image (multipart/form-data). OCR integration TBD.
- GET `/export`: Download Excel report of captured serials

### Project layout
```
app/
  main.py
  db.py
  routers/
    serials.py
  services/
    export.py
  utils/
    validation.py
```

Data stored in `data/app.db`. Exports saved to `exports/`.

### Project context
The project research, plans, and diagrams are organized under `context/`:
- `context/plan.md`
- `context/project.md`
- `context/prototype plan.md`
- Diagrams and images: `context/ocr/`
