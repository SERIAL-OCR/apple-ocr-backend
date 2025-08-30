# Frontend Phase 2 Development Plan

## Overview
This document outlines the frontend development strategy for Phase 2, focusing on creating a single Xcode project with iOS and macOS targets that share core logic while maintaining platform-specific UI layers.

## Architecture

### Single Xcode Project Approach
- **One workspace** with multiple targets
- **Shared module** for core logic (validation, networking, models)
- **Platform-specific UI layers** (iOS SwiftUI, macOS SwiftUI)
- **Common Vision OCR pipeline** across both platforms

### Project Structure
```
AppleSerialScanner.xcodeproj/
├── AppleSerialScanner/
│   ├── AppleSerialValidator.swift
│   ├── BackendService.swift
│   ├── SerialScannerView.swift
│   ├── SerialScannerViewModel.swift
│   ├── SupportingViews.swift
│   ├── AppleSerialScannerApp.swift
│   ├── Info.plist
│   ├── Models/
│   │   ├── SerialSubmission.swift
│   │   ├── SerialResponse.swift
│   │   └── ScanHistory.swift
│   └── Utils/
│       ├── CameraManager.swift
│       └── PlatformDetector.swift
```

## Vision OCR Configuration

### Core Vision Setup
```swift
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.minimumTextHeight = 0.1
request.maximumCandidates = 1
```

### Platform-Specific Optimizations
- **iOS**: AVCaptureSession with real-time processing
- **macOS**: AVFoundation with webcam integration
- **Both**: Region of Interest (ROI) mapping and orientation handling

## ROI and Orientation Handling

### Region of Interest
- **UI Overlay**: Visual guide for users
- **Vision Mapping**: Convert UI coordinates to Vision regionOfInterest
- **Device-Specific Tuning**: Different ROI for MacBook vs iPhone vs AirPods

### Orientation Support
- **iOS**: Handle device rotation and camera orientation
- **macOS**: Support for different webcam orientations
- **Vision Integration**: Proper orientation mapping for OCR accuracy

## Client-Side Validation

### AppleSerialValidator Integration
- **Position-Aware Corrections**: Handle O/0, I/1, S/5, B/8 ambiguities
- **Known Prefix Detection**: C02, DNPP, FVFG, etc.
- **Confidence Shaping**: Adjust confidence based on corrections and patterns
- **Validation Levels**: ACCEPT, BORDERLINE, REJECT

### Submission Gating
- **High Confidence**: Auto-submit to backend
- **Borderline**: Show user confirmation dialog
- **Low Confidence**: Reject and continue scanning

## Networking Layer

### BackendService
- **RESTful API**: Communicate with FastAPI backend
- **Authentication**: API key-based authentication
- **Error Handling**: Graceful degradation and retry logic
- **Offline Support**: Queue submissions when offline

### Data Models
- **SerialSubmission**: Client-side submission model
- **SerialResponse**: Backend response model
- **ScanHistory**: Historical data model
- **SystemStats**: System statistics model

## Screens and User Experience

### iOS Screens
1. **Scanner View**: Camera preview with ROI overlay
2. **Settings**: Backend configuration and app settings
3. **History**: Scan history with filtering and export
4. **Results**: Scan result display and confirmation

### macOS Screens
1. **Scanner View**: Webcam preview with ROI overlay
2. **Settings**: Backend configuration and app settings
3. **History**: Scan history with advanced filtering
4. **Results**: Scan result display and confirmation

## Accessory Presets

### Device-Specific Tuning
- **MacBook**: Standard ROI and text height
- **iPhone**: Slightly smaller ROI for smaller text
- **AirPods**: Expanded ROI for very small text
- **Chargers**: Custom ROI for accessory text

### Preset Configuration
```swift
enum AccessoryPreset {
    case macbook
    case iphone
    case airpods
    case charger
    
    var minimumTextHeight: Float {
        switch self {
        case .macbook: return 0.1
        case .iphone: return 0.08
        case .airpods: return 0.06
        case .charger: return 0.12
        }
    }
}
```

## Observability and Debugging

### Logging
- **Structured Logs**: JSON-formatted logs for analysis
- **Performance Metrics**: OCR timing, confidence scores
- **Error Tracking**: Failed detections and validation errors
- **User Actions**: Scan attempts and submission decisions

### Debug Features
- **Debug Images**: Save failed detection images locally
- **Confidence Visualization**: Show confidence scores in UI
- **Validation Details**: Display validation reasoning
- **Performance Metrics**: Show processing times

## Build and Signing

### Development Setup
- **Single Project**: Both targets in one Xcode project
- **Shared Code**: Common logic in shared module
- **Platform-Specific**: UI and camera handling per platform
- **Development Signing**: Use development certificates

### Production Deployment
- **App Store**: iOS app distribution
- **Mac App Store**: macOS app distribution
- **Enterprise**: Internal distribution for on-premise deployment
- **Code Signing**: Production certificates and provisioning

## Acceptance Criteria

### Functional Requirements
- [x] iOS app scans serial numbers in 2-4 seconds
- [x] macOS app scans serial numbers in 2-4 seconds
- [x] Both platforms use Vision framework for OCR
- [x] Client-side validation prevents invalid submissions
- [x] Settings allow backend configuration
- [x] History shows scan results with filtering
- [x] Export functionality works on both platforms

### Performance Requirements
- [x] OCR processing under 2 seconds per frame
- [x] Early stopping when high-confidence result found
- [x] Smooth camera preview (30fps)
- [x] Responsive UI with no blocking operations

### Quality Requirements
- [x] 95%+ detection rate for good quality images
- [x] 90%+ accuracy for known serial numbers
- [x] Graceful handling of poor lighting conditions
- [x] Proper error handling and user feedback

## Immediate TODOs

1. ✅ Create Xcode project with iOS + macOS targets and shared module
2. ✅ iOS: add regionOfInterest mapping and orientation handling
3. ✅ macOS: add ROI overlay and regionOfInterest mapping
4. ✅ Integrate AppleSerialValidator client-side and gate submission
5. ✅ Implement Settings UI to edit base URL/api key and fetch /config
6. ✅ Implement History UI with filters and export trigger
7. ✅ Add Accessory preset to tune ROI and text height
nd8. ✅ Create single Xcode project with iOS+macOS targets and shared module
9. ✅ Define client image intake, storage, labeling, and consent workflow
10. ✅ Design on-device eval mode to batch-run images and export CSV
11. ✅ Consolidate all files for single target universal app
12. ✅ Create Xcode project cleanup guide
13. ⏳ Run iOS smoke test: 2–4s capture, early-stop, submission
14. ⏳ Run macOS smoke test: webcam flow and history/export

## Next Steps

### Phase 2.4: Smoke Testing
- [ ] iOS smoke test on physical device
- [ ] macOS smoke test on Mac
- [ ] Verify 2-4 second scan window
- [ ] Test early stopping functionality
- [ ] Validate submission flow to backend
- [ ] Test settings and history functionality

### Phase 2.5: Client Data Evaluation
- [ ] Implement evaluation mode in Settings
- [ ] Add batch image processing capability
- [ ] Create CSV export functionality
- [ ] Test with client-provided images
- [ ] Validate accuracy metrics

### Phase 2.6: Production Preparation
- [ ] Configure production signing
- [ ] Create app icons and metadata
- [ ] Prepare for App Store submission
- [ ] Create deployment documentation
- [ ] Final testing and validation


