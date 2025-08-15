## Apple Serial Number OCR – Consolidated Project Context (Backend + iOS)

This document consolidates the project vision, MVP plan, system architecture, endpoints, and references for both backend and iOS integration. It’s intended for engineers working on both repos (backend and frontend/iOS).

### Repositories and Sources
- Backend (this repo): `apple-ocr-backend`
- iOS UI (frontend repo): separate; leveraging `StewartLynch/Live-Text-in-iOS-16`
- Vendor OCR reference copied locally: `vendor/ipad-ocr` (from `jornl/ipad-ocr`)
- Research assets: `context/ocr/` (diagrams, images)

### Executive Summary
We are building an OCR system to extract 12-character Apple device serial numbers from images. Phase 1 delivers a 7-day MVP to validate feasibility (target 90%+ accuracy), followed by Phase 2 which expands to a robust, enterprise-grade system.

### MVP Objectives and Metrics
- Objective: Working prototype in 7 days to secure client approval
- Metrics:
  - OCR Accuracy: target 90%+, acceptable 85%
  - Processing Speed: < 3 s end-to-end (acceptable < 5 s)
  - Stability: 50+ serials continuous operation (acceptable 20+)
  - Demo Quality: smooth 10-minute demo (core features shown minimum)

### Technology Stack (Phase 1)
- Backend: FastAPI (Python 3.11)
- OCR: EasyOCR (with OpenCV preprocessing)
- Storage: SQLite (MVP); Excel export via `openpyxl`
- iOS: Native Swift using VisionKit (`DataScannerViewController`) or Live Text
- Deployment: Docker + Docker Compose

### Backend Endpoints (MVP)
- `GET /health` – Health check
- `POST /process-serial` – Multipart file upload parameter `image`; runs OCR and returns candidate serials with confidence. Persists the top result to SQLite.
- `GET /export` – Streams an Excel report of stored serials

### Backend Directory Layout
```
app/
  main.py                # FastAPI app and health route
  db.py                  # SQLite helpers and table init
  routers/
    serials.py           # /process-serial and /export
  services/
    export.py            # Excel export (openpyxl)
  utils/
    validation.py        # 12-char Apple serial validator
  pipeline/
    ocr_adapter.py       # EasyOCR + OpenCV preprocessing

vendor/
  ipad-ocr/              # Copied reference repo (no .git / license)

context/
  ocr/                   # Diagrams, charts, images
  plan.md                # High-level plan
  project.md             # Phased development plan (formatted)
  prototype plan.md      # 7-day MVP daily breakdown (formatted)
```

### iOS Integration Notes (Frontend)
- Use Apple’s VisionKit (`DataScannerViewController`) or Live Text to detect text client-side for UX; send the captured image (or cropped region) to the backend via `POST /process-serial`.
- Acceptable media types: `image/jpeg`, `image/png`, `image/heic`, `image/heif`.
- For MVP, send full-frame images; cropping can be added in-app to improve accuracy.

### OCR Pipeline (MVP)
- Preprocessing: grayscale → CLAHE → bilateral filter → adaptive threshold (OpenCV)
- OCR: EasyOCR English model (`easyocr.Reader(["en"])`)
- Validation: 12-character `[A-Z0-9]{12}`; uppercased, spaces removed
- Persistence: top-confidence valid serial saved with timestamp and optional device type

### Day 1 Deliverables (Completed)
- FastAPI scaffold with CORS
- SQLite storage and Excel export
- OCR adapter with EasyOCR and preprocessing
- Dockerfile and docker-compose
- Context re-organization and vendor repo copy
- Samples folder with synthetic test images; quick smoke test script

### Prototype (7-Day) Plan (Condensed)
- Day 1 – Environment & Scaffold: venv, deps, FastAPI skeleton, OCR wiring, Docker
- Day 2 – OCR & Processing: refine preprocessing, improve extraction accuracy (90%+ target)
- Day 3 – Validation & API: finalize 12-char validation, test endpoints, error handling
- Day 4 – iOS Integration: scanning UI via VisionKit; connect to backend
- Day 5 – Export & Polish: Excel export, performance optimizations
- Weekend – Buffer & Docs: bug fixes, demo prep
- Day 6 – Demo Day: 10–15 min live demo, feedback, next steps

For detailed prose, see:
- `context/project.md` – Phased plan with metrics, risks, and deployment
- `context/prototype plan.md` – Daily tasks and deliverables
- `context/plan.md` – Prompts and structured plan content

### Phase 2 (Future)
- Advanced Validation: Integrate Apple APIs for real-time verification
- Batch Processing: High-throughput ingestion and processing
- Data Platform: Migrate SQLite → Postgres; add Alembic migrations
- Security: AuthN/AuthZ, audit logs
- Observability: metrics, tracing, dashboards
- Deployment: Hardened Docker/Compose, CI/CD, on-prem support

### Sample Testing
- Put test images under `samples/`
- Test upload via PowerShell:
  - `.	emplates":[this section is not code; ignore]`
  - Example: `Invoke-WebRequest -Uri http://localhost:8000/process-serial -Method Post -Form @{ image = Get-Item .\samples\img1.jpg } | Select-Object -ExpandProperty Content`

### References
- `vendor/ipad-ocr` from `jornl/ipad-ocr` – pipeline structure and preprocessing inspiration
- iOS UI reference: `StewartLynch/Live-Text-in-iOS-16` – Live Text / VisionKit code patterns
- Diagrams & images under `context/ocr/`

---
This document is kept in the backend repo for easy access. A copy should be placed in the frontend/iOS repo for onboarding and implementation alignment.
