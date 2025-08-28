## Frontend Phase 2 Plan — Vision-based Apple Serial Scanner (iOS + macOS)

### 1) Objectives
- Deliver an on-device OCR experience that matches Apple Support-like scanning: 2–4s capture, ≥95% accuracy, no image uploads.
- Support iOS (primary) and macOS (secondary) in a single Xcode project with two targets.
- Client validates serials before submission; backend stores, filters, exports.

### 2) Architecture Overview
- Single Xcode project with two app targets: “AppleSerialScanner iOS” and “AppleSerialScanner macOS”.
- Shared code module for networking, models, validation, configuration.
- Platform-specific camera + UI layers using Vision + AVFoundation.
- Backend contract: `POST /serials`, `GET /history`, `GET /export`, `GET /config`, `GET /stats`.

### 3) Project Structure (proposed)
- Shared/
  - Networking: `BackendService.swift`
  - Models: request/response DTOs
  - Validation: `AppleSerialValidator` (client-side port)
  - Utilities: configuration, formatting
- iOS/
  - `SerialScannerViewModel.swift` (Vision pipeline, ROI, orientation)
  - `SerialScannerView.swift` (UI: preview, overlay, status, controls)
  - `SettingsView.swift`, `HistoryView.swift` (client UI)
- macOS/
  - `SerialScannerView.swift` (includes macOS ViewModel + views)

### 4) Vision OCR Configuration (baseline)
- `VNRecognizeTextRequest` with:
  - `recognitionLevel = .accurate`
  - `usesLanguageCorrection = false` (reduce swaps like O↔0, I↔1)
  - `recognitionLanguages = ["en-US"]`
  - `minimumTextHeight` tuned by device and preset
- Processing window and best-of-N:
  - 2–4s rolling window, up to 10 frames; early-stop at confidence ≥0.85
  - Submit only if best frame ≥ minAcceptanceConfidence (from `/config`)

### 5) ROI, Orientation, and Heuristics
- Map on-screen ROI rectangle to `regionOfInterest` in Vision (normalized coordinates) per device orientation.
- Adaptive ROI height (default ~20% of width; accessory preset ~12–18%).
- Torch/lighting guidance (iOS); exposure suggestions (macOS).
- If no candidate in ~2s, widen ROI slightly and show tilt/align guidance.

### 6) Client-side Validation and Submission Gate
- Integrate `AppleSerialValidator`:
  - Position-aware corrections (O/0, I/1, S/5, B/8) by index.
  - Known prefix detection and confidence shaping.
  - Levels: ACCEPT, BORDERLINE (user confirm), REJECT.
- Only submit when ACCEPT, or BORDERLINE with user confirmation.

### 7) Networking and Configuration
- `BackendService` reads `backend_base_url`, `api_key` from `UserDefaults`.
- Fetch `/config` at startup to set thresholds (min acceptance/submission).
- Submit payload: `serial`, `confidence`, `device_type` ("iOS"/"Mac"), `source` ("ios"/"mac"), `ts`, optional `notes`.

### 8) Screens and UX
- Scanner screen: live preview, ROI overlay, guidance text, best-confidence chip, manual capture, flash toggle (iOS).
- Settings: edit base URL, API key, presets (Default/Accessory), threshold toggles; persist to `UserDefaults`.
- History: fetch from `/history` with filters; list with status, confidence; export button triggers `/export`.

### 9) Accessory Presets (AirPods, Chargers)
- Quick preset toggle modifies:
  - ROI height (slightly larger), `minimumTextHeight`, processing window if needed.
  - Guidance text (“Move closer”, “Increase light”).

### 10) Observability
- Structured logs (in-app): detection window, frames processed, best confidence, validator level, submit outcome.
- Optional debug overlay for development builds.

### 11) Build, Signing, Deployment
- Two targets, shared code.
- iOS: `NSCameraUsageDescription`, ATS dev exception for localhost.
- macOS: camera entitlement; ATS dev exception as needed.
- Deployment targets: iOS 15+, macOS 12+.

### 12) Acceptance Criteria
- iOS: median end-to-end ≤4s; ≥95% valid serial accuracy on pilot set.
- macOS: parity for desk workflows; stable detection of small engravings.
- No image uploads; all privacy-sensitive processing on-device.

### 13) Immediate TODOs (Phase 2 current focus)
1. Create Xcode project (single workspace) with iOS + macOS targets using shared module.
2. iOS: add ROI → `regionOfInterest` mapping and orientation handling in `SerialScannerViewModel`.
3. macOS: add ROI overlay and `regionOfInterest` mapping; parity with iOS pipeline.
4. Integrate `AppleSerialValidator` before submission; gate on ACCEPT/BORDERLINE.
5. Settings UI: edit/persist `backend_base_url`, `api_key`, preset selector; fetch `/config` on launch.
6. History UI: fetch from `/history`, basic filters, export trigger to `/export`.
7. Accessory preset: tune ROI height and `minimumTextHeight`; adjust guidance.
8. Smoke test on iPhone and Mac webcam; verify 2–4s window, early-stop, and submission.

Notes:
- We will only deviate from this plan when ≥95% certain the change improves latency/accuracy or stability.
- Keep legacy EasyOCR paths out of scope; this is fully on-device.


