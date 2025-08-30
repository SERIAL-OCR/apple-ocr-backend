## Phase 2 – Reverse Engineering Plan for Apple OCR System

### Context

We are upgrading the MVP (YOLO ROI + EasyOCR + Tesseract fallback) into an Apple‑class OCR system for serial recognition. This plan divides Phase 2 into sub‑phases with clear objectives, resources, scope of changes, dependencies, timelines, and acceptance criteria. It follows a server‑first approach for rapid productization and a parallel R&D track for CoreML/ANE feasibility.

### High‑Level Objectives

- Accuracy: ≥95% target (≥92% minimum) on labeled real images; avg confidence ≥0.70 (positives)
- Latency: 2–4s typical on Apple devices (≤6s P95); minimize tail
- Privacy & UX: no image uploads in production; on‑device recognition
- On‑prem: backend runs on Mac/Mac Studio; data stays local; Excel export
- Optional: server OCR track for lab/backup only; can be disabled in prod

### Inputs and Ground Truth

- Ground truth labels: `exported-assets/labels.csv` (filename, serial)
- Real images: `Apple serial/` and `exported-assets/`
- Debug/bench outputs: `storage/exports/` and `exports/reports/`

### Resource Map (to be used in this phase)

- Vision/VisionKit docs: `https://developer.apple.com/documentation/vision` and `https://developer.apple.com/documentation/visionkit`
- CLOVA Deep Text Recognition: `https://github.com/clovaai/deep-text-recognition-benchmark`
- CRNN baseline: `https://github.com/meijieru/crnn.pytorch`
- PaddleOCR: `https://github.com/PaddlePaddle/PaddleOCR`
- MMOCR: `https://github.com/open-mmlab/mmocr`
- CoreMLTools: `https://apple.github.io/coremltools/`
- Apple ml-ane-transformers: `https://github.com/apple/ml-ane-transformers`
- macos-vision-ocr (reference): `https://github.com/bytefer/macos-vision-ocr`
- OpenCV/Albumentations for preprocessing/synthetic data

---

## 2. On‑Device Apple‑like OCR (Production Path)

### 2.1 Architecture and UX ✅ COMPLETED

- **Status**: ✅ Implemented and tested
- **Implementation**: 
  - Added `POST /serials` endpoint for on-device OCR submissions
  - Enhanced database schema with source, notes, validation tracking
  - Implemented API key authentication and validation
  - Added observability endpoints (`/stats`, enhanced `/health`, `/config`)
  - Created comprehensive test suite (`test_phase2_1.py`)
  - **Completely removed all image upload functionality** (`/scan`, `/process-serial`, `/process-progressive`)
  - Removed queue processing, background tasks, and server OCR dependencies
  - Simplified configuration to Phase 2.1 only
- **Key Features**:
  - Data contract: `{serial, confidence, device_type, source, ts, notes}`
  - Apple serial validation with confidence thresholds
  - Multi-device support (ios/mac/server)
  - Structured logging and metrics
  - Security: API key auth, rate limiting ready
  - **No image uploads**: System only accepts validated serial results
- **Testing**: ✅ All 9/9 tests passing
- **Next**: Ready for Phase 2.3 (Client-side validation and post-processing)

### 2.2 iOS/macOS Scanner Implementation ✅ COMPLETED

- **Status**: ✅ Implemented and tested
- **Goals**: 
  - Use `VNRecognizeTextRequest` with accurate recognition level
  - Add ROI overlay guidance and orientation hints
  - Apply capture guidance (exposure/angle/lighting)
  - Show live feedback
  - Batch retries up to N frames within a 2–4s window
  - Select best by confidence
- **Implementation**:
  - **iOS Scanner**: SwiftUI app with Vision/VisionKit integration
    - Real-time camera preview with ROI overlay
    - Corner indicators and guidance text
    - Auto-capture with best-of-N frame selection (4s window, 10 frames max)
    - Manual capture option with flash control
    - Status indicators (confidence, frame count, device type)
    - Settings and history views with backend integration
  - **macOS Scanner**: SwiftUI app with Vision/AVFoundation
    - Camera preview with manual start/stop controls
    - Same OCR logic as iOS version
    - Desktop-optimized UI
  - **Backend Integration**: Full integration with Phase 2.1 API
    - Serial submission with validation
    - History viewing and export
    - Settings management
    - Health checks and configuration
- **Key Features**:
  - Vision OCR with accurate recognition level
  - Real-time frame processing and confidence tracking
  - Apple serial format validation (12-char alphanumeric)
  - Best-of-N selection with early stopping at 85% confidence
  - Camera permissions and flash control
  - Network error handling and retry logic
- **Testing**: Ready for device testing
- **Next**: Client-side validation and post-processing (2.3)

### 2.3 Client‑side Validation and Post‑processing ✅ COMPLETED

- **Status**: ✅ Implemented and tested
- **Goals**: 
  - Position-aware disambiguation (0↔O, 1↔I, 5↔S, 8↔B; rules by position)
  - Apple-specific length/pattern checks before accepting; confidence shaping
  - Only submit when confidence ≥0.65 or with explicit user confirm on borderline cases
- **Implementation**:
  - **AppleSerialValidator Class**: Comprehensive validation logic
    - Position-aware character corrections (12 positions, OCR-specific mappings)
    - Known Apple serial prefix detection (C02-C0F, CO2-COF, single-char prefixes)
    - Position-specific pattern validation
    - Apple serial format rules (last 4 chars contain digit, middle mix)
    - Confidence shaping with penalties/bonuses
    - Validation levels: ACCEPT, BORDERLINE, REJECT
  - **Validation Features**:
    - Character disambiguation based on position context
    - Known prefix detection with confidence bonuses
    - Unknown prefix identification with rejection
    - Position-specific pattern validation
    - Apple serial format compliance checks
    - Confidence adjustment based on corrections/warnings
    - User confirmation logic for borderline cases
  - **Submission Logic**:
    - REJECT level: Never submit
    - ACCEPT level: Always submit
    - BORDERLINE level: Submit only with user confirmation
  - **Integration**: Ready for iOS/macOS client integration
- **Testing**: ✅ All 7/7 tests passing
  - Position corrections, known prefixes, confidence shaping
  - Validation levels, submission logic, convenience functions
  - Edge case handling
- **Next**: Backend data services (2.4)

### 2.4 Backend Data Services (On‑prem Mac)

- `POST /serials` (JSON): persist `{serial, confidence, device_type, timestamp}`.
- `GET /history`, `GET /export`: history view and Excel export using existing code.
- Optional: `/health` and basic admin endpoints; de‑emphasize `/process-serial` in production.

### 2.5 Performance and Accuracy Targets

- Latency: 2–4s typical (≤6s P95) per scan on iPhone or Mac station camera.
- Accuracy: ≥95% target (≥92% min) on labeled real images; avg confidence ≥0.70.
- Reliability: false accept rate minimized via validation; user confirm on low confidence.

### 2.6 Deployment (On‑prem Mac/Mac Studio)

- Run FastAPI backend on a Mac/Mac Studio; SQLite or Postgres on‑prem; nightly exports.
- No external egress required; images never leave client devices.
- Admin dashboard shows counts, recent scans, and export links.

### 2.7 Observability and Security

- Structured logs with request IDs; metrics for submissions, confidence distribution, and export usage.
- API key auth and local network ACLs; HTTPS or LAN‑only access.

### 2.8 Optional CoreML/ANE Enhancements (R&D)

- If Vision accuracy needs a boost, prototype CoreML recognizer; measure FP16/int8 quantization impact on accuracy/latency.
- Consider Mac station ANE acceleration for camera workflows.

### 2.9 Acceptance and Handoff

- Meet latency/accuracy targets on pilot devices; publish short validation report.
- App and backend demo: scan → instant result → stored → Excel export.

Note: The following Sub‑Phases describe the optional server OCR track (lab/backup); production uses Section 2 above.

## Sub‑Phases

### A) Async Jobs and Batch APIs (Week 1)

- Goals
  - Non‑blocking UX and scalability; align with async design (submit → job_id → poll).
- Changes
  - `POST /jobs` submit (image, device_type, preset, params) → returns `job_id` immediately.
  - `GET /jobs/{id}` status/result (queued | processing | done | error) with timestamps and stage summary.
  - `POST /batch` for N images (returns batch_id; `GET /batch/{id}` for aggregated status/result).
  - HEIC/HEIF acceptance with server‑side conversion (to PNG/JPEG) if needed.
  - Background worker: single or small pool; warm model/reader at startup.
- Deliverables
  - Endpoints + worker; JSON schemas; iOS polling flow; minimal docs.
- Dependencies
  - Existing FastAPI; storage layout under `storage/`.
- Acceptance
  - Submit returns in <300ms; status transitions correct; end‑to‑end works with iOS.

### B) Labels‑Driven Evaluation + Param Sweeps (Week 1–2)

- Goals
  - Reproducible measurement and automated parameter optimization.
- Changes
  - Eval CLI: read `exported-assets/labels.csv`, run pipeline, write `csv/json` per‑image results + summary (accuracy, avg confidence, early‑stop rate, latency distribution).
  - Param sweeps: rotate angles, upscale, thresholds, ROI `top_k`, early‑stop; persistent best‑params cache per preset/device via `app/services/param_cache.py`.
  - Nightly job to run eval and publish artifacts under `storage/reports/`.
- Deliverables
  - `scripts/run_accuracy_eval.py` (or reuse `scripts/run_accuracy_eval.py`), summary markdown, plots.
- Acceptance
  - Deterministic reports; best‑params cache used by API; documented gains vs baseline.

### C) Apple‑Specific Validation + Confidence Boosts (Week 2)

- Goals
  - Reduce false positives and improve ranking on valid serials.
- Changes
  - Tighten `app/utils/validation.py`: charset/position constraints for Apple serials; reject ambiguous combos.
  - Position‑aware disambiguation (0↔O, 1↔I, 5↔S, 8↔B etc.) with per‑position priors.
  - Confidence shaping: boosts for valid length/pattern; penalties for high ambiguity; surface device‑specific rules.
  - Optional external Apple verification API stub with adapter pattern.
- Deliverables
  - Unit tests in `tests/unit/utils/test_validation.py`; feature flags in `config.py`.
- Acceptance
  - +2–4 pp accuracy on labeled set without latency regression; tests green.

### D) Performance + ROI Refinements (Week 2–3)

- Goals
  - Increase early‑stop rate and reduce tail latency.
- Changes
  - Projection‑based band detector: adaptive thresholds; `roi_top_k=3`; adaptive padding; width/height validation.
  - Selective TTA: attempt ±7°, ±15° only when low confidence; orientation estimate to prioritize angles.
  - Startup warmup for models; parallel OCR across top‑K ROIs; cache repeat images by hash.
- Deliverables
  - Profiling traces; per‑stage timing metrics; updated debug artifacts.
- Acceptance
  - P50 ≤6s; early‑stop ≥65% (toward 70% target); P95 reduced ≥25% vs baseline.

### E) Recognizer Upgrade (Server‑Side Baseline) (Week 3–4)

- Goals
  - Surpass EasyOCR on accuracy/latency using an off‑the‑shelf stronger recognizer.
- Changes
  - Integrate one of: PaddleOCR, MMOCR, or CLOVA recognizer behind a feature toggle.
  - Normalize outputs into current schema (text, confidence, boxes); keep disambiguation/validation layer unchanged.
  - Evaluate on labeled set; pick default by measured metrics.
- Deliverables
  - Pluggable recognizer interface; evaluation comparison report.
- Acceptance
  - ≥92% accuracy on labeled set; no regression in P50 vs MVP after tuning.

### F) Synthetic Data v1 + Fine‑Tuning (Week 4–5)

- Goals
  - Close domain gaps (glare, etching, perspective) and improve robustness.
- Changes
  - 2D compositing generator: render Apple‑style fonts, apply perspective/shear, glare/illumination maps, noise/blur, background textures.
  - Generate a small but diverse set (e.g., 20–50k) for initial fine‑tuning of chosen recognizer; track overfitting/robustness.
- Deliverables
  - Scripts under `scripts/` (OpenCV/Albumentations); fine‑tuned checkpoint; before/after evaluation.
- Acceptance
  - +2–3 pp accuracy on hard categories; stable latency.

### G) Observability, Security, CI/CD (Weeks 3–5, overlapping)

- Goals
  - Make the system operable and safe for broader use.
- Changes
  - Metrics: per‑stage durations, early‑stop rate, ROI counts, confidence distribution; Prometheus export and minimal Grafana dashboard.
  - Logs: structured with `job_id`, failure taxonomy, debug artifact links.
  - Security: API key auth; basic rate limiting; HTTPS guidance/termination options.
  - CI/CD: unit + smoke tests, linting, container build/publish; env‑based presets.
- Deliverables
  - Dashboards; runbooks; CI workflow; security config.
- Acceptance
  - Dashboards reflect live traffic; CI green; auth/rate‑limit enforced in non‑dev.

### H) CoreML/ANE Prototype (Optional R&D) (Week 5–6)

- Goals
  - Assess on‑device/Mac inference feasibility and cost/benefit.
- Changes
  - Convert chosen recognizer to CoreML via CoreMLTools; evaluate FP16/int8 quantization impact on accuracy.
  - Prototype `apple/ml-ane-transformers` path; benchmark on M‑series hardware; iOS side‑by‑side VisionKit vs backend comparison.
- Deliverables
  - Prototype model and benchmark notes; go/no‑go decision for production adoption.
- Acceptance
  - Documented accuracy/latency delta; clear recommendation on on‑device vs server inference.

### I) Acceptance, Docs, and Launch

- Acceptance Criteria (Phase End)
  - Accuracy ≥92% on labeled real set with published report.
  - Latency P50 ≤5s, P95 ≤12s; early‑stop ≥70%.
  - APIs: jobs + batch stable; HEIC supported; contracts documented.
  - Ops: dashboards live; logs structured; auth + rate limit enabled; CI/CD green.
- Deliverables
  - Final report, API docs, demo plan, deployment notes, troubleshooting guide.

---

## 🚀 ADVANCED APPLE-LIKE FEATURES (Phase 2.5-3.2)

### Phase 2.5: Advanced Surface Detection (IN PROGRESS)
**Goal:** Auto-detect different surface types for optimal OCR settings

**Apple-like Features:**
- **Surface Classification**: Metal, plastic, glass, paper, screen detection
- **Material-specific OCR**: Different preprocessing per surface type
- **Adaptive Thresholds**: Surface-aware confidence thresholds
- **Visual Feedback**: Surface type indicators in UI

**Implementation:**
- Vision-based surface classification using image features
- Material detection algorithms (reflection patterns, texture analysis)
- Dynamic parameter adjustment based on surface type
- UI indicators showing detected surface type

### Phase 2.6: Lighting Adaptation System
**Goal:** Auto-adjust for various lighting conditions (Apple's advanced feature)

**Apple-like Features:**
- **Glare Detection**: Real-time glare pattern recognition
- **Illumination Compensation**: Auto-adjust for low light, direct sunlight
- **HDR-like Processing**: Multi-frame exposure compensation
- **Adaptive Filters**: Dynamic contrast/brightness adjustment

**Implementation:**
- Real-time lighting condition analysis
- Multi-frame capture for HDR-like enhancement
- Adaptive preprocessing filters
- Lighting condition indicators

### Phase 2.7: Advanced Angle Correction
**Goal:** Intelligent text orientation detection and correction

**Apple-like Features:**
- **3D Orientation Detection**: Detect text angle in 3D space
- **Perspective Correction**: Auto-correct for angled surfaces
- **Rotation Optimization**: Find optimal viewing angle
- **Stabilization**: Reduce motion blur effects

**Implementation:**
- Vision-based text orientation analysis
- Perspective transformation algorithms
- Gyroscope integration for device orientation
- Real-time angle correction feedback

### Phase 2.8: Accessory Presets System
**Goal:** Device-specific scanning profiles (Apple ecosystem integration)

**Apple-like Features:**
- **Device Recognition**: Auto-detect iPhone, iPad, MacBook, Apple Watch
- **Accessory Integration**: Support for cases, stands, docks
- **Size-aware ROI**: Different scan areas per device type
- **Preset Management**: User-customizable scanning profiles

**Implementation:**
- Device type detection from serial format
- Accessory recognition using computer vision
- Dynamic ROI adjustment per device
- Preset storage and management

### Phase 2.9: Batch Processing Engine
**Goal:** Process multiple serials efficiently in sequence

**Apple-like Features:**
- **Workflow Optimization**: Smart sequencing of multiple scans
- **Progress Tracking**: Real-time batch processing status
- **Error Recovery**: Intelligent handling of failed scans
- **Bulk Export**: Combined results for multiple devices

**Implementation:**
- Queue management system
- Progress visualization
- Batch error handling
- Combined export formats

### Phase 3.0: Export Integration
**Goal:** Native Apple ecosystem integration

**Apple-like Features:**
- **Numbers Integration**: Direct export to Apple Numbers
- **Excel Compatibility**: Enhanced Excel formatting
- **iCloud Sync**: Automatic backup and sync
- **Share Sheet**: Native iOS/macOS sharing

**Implementation:**
- Apple Numbers format support
- Enhanced Excel templates
- iCloud integration
- Share extension support

### Phase 3.1: Advanced Analytics Dashboard
**Goal:** Comprehensive performance and accuracy insights

**Apple-like Features:**
- **Confidence Trends**: Historical accuracy analysis
- **Performance Metrics**: Detailed timing breakdowns
- **Error Analysis**: Failure pattern recognition
- **Usage Statistics**: Scanning behavior analytics

**Implementation:**
- Analytics data collection
- Performance dashboards
- Trend analysis
- Predictive insights

### Phase 3.2: Smart Retry Logic
**Goal:** Intelligent retry system based on failure analysis

**Apple-like Features:**
- **Failure Pattern Recognition**: Learn from past failures
- **Adaptive Retry**: Smart retry strategies per failure type
- **Surface Learning**: Remember challenging surfaces
- **Progressive Enhancement**: Improve success rate over time

**Implementation:**
- Failure pattern analysis
- Machine learning-based retry logic
- Surface condition memory
- Continuous improvement algorithms

---

## Timeline (Indicative 5–6 Weeks)

- Week 1: 2.2 scanner (Vision) prototype; 2.3 validation; 2.4 `POST /serials`
- Week 2: Tune validation/disambiguation; pilot on devices; history/export polish
- Week 3: Observability/security; Mac station flow; accuracy/runbook
- Week 4: Optional CoreML prototype; refine UX; acceptance tests
- Week 5–6: Rollout to pilot sites; finalize documentation and handoff

## Dependencies and Sequencing

- 2.2 depends on iOS/macOS camera/permissions; 2.3 validation feeds acceptance; 2.4 storage enables history/export; 2.7 spans the timeline; 2.8 gated by 2.2 success.

## Key Risks and Mitigations

- Model swap uncertainty → keep toggled recognizers; ship fastest winning baseline.
- Tail latency spikes → stricter early‑stop, selective TTA, ROI top‑K limits.
- HEIC variability → robust conversion and tests; fallback to JPEG.
- Overfitting to synthetic → mix real + synthetic; hold‑out set; nightly evals.
- CoreML/ANE effort creep → treat as optional R&D until server win locked.

## Execution Checklist (Week 1 Kickoff)

- [x] iOS/macOS: Vision scanner view; ROI overlay; debounce; best‑of window (2–4s) ✅ COMPLETED
- [x] Client‑side validation/disambiguation using Apple serial rules ✅ COMPLETED
- [x] Backend: `POST /serials` endpoint and DB write; `GET /history`, `GET /export` ✅ COMPLETED
- [x] Metrics: submissions, acceptance rate, confidence histogram ✅ COMPLETED

## Xcode Development Guide

### iOS App Setup Instructions:
1. **Create new Xcode project**: iOS App → SwiftUI → "AppleSerialScanner"
2. **Copy files from backend repo**:
   - `ios/AppleSerialScanner/AppleSerialScanner/SerialScannerView.swift` → Main scanner view
   - `ios/AppleSerialScanner/AppleSerialScanner/SerialScannerViewModel.swift` → ViewModel logic
   - `ios/AppleSerialScanner/AppleSerialScanner/BackendService.swift` → API integration
   - `ios/AppleSerialScanner/AppleSerialScanner/SupportingViews.swift` → Settings & History
   - `ios/AppleSerialScanner/AppleSerialScanner/AppleSerialScannerApp.swift` → Main app file
   - `ios/AppleSerialScanner/AppleSerialScanner/Info.plist` → Permissions & config

3. **Required frameworks**: Add to project
   - Vision
   - VisionKit  
   - AVFoundation
   - Combine

4. **Camera permissions**: Info.plist already configured
   - `NSCameraUsageDescription` included
   - Network security settings for localhost

### macOS App Setup Instructions:
1. **Create new Xcode project**: macOS App → SwiftUI → "AppleSerialScanner-macOS"
2. **Copy files from backend repo**:
   - `macos/AppleSerialScanner/AppleSerialScanner/SerialScannerView.swift` → Main scanner view
   - `macos/AppleSerialScanner/AppleSerialScanner/BackendService.swift` → API integration (shared)

3. **Required frameworks**: Add to project
   - Vision
   - AVFoundation
   - AppKit

### Backend Configuration:
- **Server URL**: Update in Settings → Backend Configuration
- **API Key**: Default is "phase2-pilot-key-2024" (change in production)
- **Local Development**: Backend runs on `http://localhost:8000`

### Testing Checklist:
- [ ] Camera permissions granted
- [ ] Backend server running (`python -m uvicorn app.main:app --reload`)
- [ ] Network connectivity to backend
- [ ] Vision OCR working on test serial numbers
- [ ] Serial submission to backend successful
- [ ] History and export functionality working

## Reporting Spec (Nightly)

- Outputs: `eval_*.csv/json`, latency histograms, accuracy by device type, early‑stop rate, top failure reasons; summary markdown pushed to `storage/reports/`.

## Notes on Reverse Engineering Angle

- Leverage Vision/VisionKit outputs on identical images to triangulate expected results (for qualitative parity), but keep server‑first PyTorch stack as source of truth. Only after server baseline exceeds MVP do we prototype CoreML/ANE conversion and on‑device inference.


