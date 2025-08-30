# Xcode Files to Copy - Single Target Universal App

## Overview
This document lists all the files you need to copy from this repository to your Xcode project. The app is designed as a single target that works on both iOS and macOS with platform-specific adaptations.

## Project Structure
Create a single Xcode project with one target that supports both iOS and macOS platforms.

## Files to Copy

### Core App Files
Copy these files to your Xcode project's main target:

1. **`AppleSerialScannerApp.swift`** - Main app entry point
2. **`Info.plist`** - App configuration (adjust bundle identifier and permissions)

### Main Views and ViewModels
3. **`SerialScannerView.swift`** - Main scanner view (universal for iOS/macOS)
4. **`SerialScannerViewModel.swift`** - Main view model (universal with platform detection)
5. **`SupportingViews.swift`** - Settings and History views (universal)

### Core Logic
6. **`AppleSerialValidator.swift`** - Client-side validation logic
7. **`BackendService.swift`** - Backend API communication

### Models
Copy the entire `Models/` folder:
8. **`Models/SerialSubmission.swift`** - Data model for serial submissions
9. **`Models/SerialResponse.swift`** - Data model for backend responses
10. **`Models/ScanHistory.swift`** - Data model for scan history
11. **`Models/SystemStats.swift`** - Data model for system statistics

### Utilities
Copy the entire `Utils/` folder:
12. **`Utils/CameraManager.swift`** - Camera management utilities
13. **`Utils/PlatformDetector.swift`** - Platform detection utilities

## Xcode Project Configuration

### Target Settings
- **Deployment Target**: iOS 15.0+ and macOS 12.0+
- **Supported Platforms**: iOS, macOS
- **Device Family**: iPhone, iPad, Mac

### Required Frameworks
Add these frameworks to your target:
- `Vision.framework`
- `VisionKit.framework` (iOS only)
- `AVFoundation.framework`
- `SwiftUI.framework`

### Required Permissions
Add to `Info.plist`:

**iOS:**
```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to scan Apple serial numbers.</string>
```

**macOS:**
```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to scan Apple serial numbers.</string>
```

### Build Settings
- **Swift Language Version**: Swift 5.0
- **iOS Deployment Target**: 15.0
- **macOS Deployment Target**: 12.0

## Platform-Specific Code

The code already includes platform-specific adaptations using:
- `#if os(iOS)` and `#if os(macOS)` compiler directives
- `PlatformDetector` utility for runtime platform detection
- Conditional UI elements (flash toggle only on iOS)
- Platform-specific camera setup

## Copy Instructions

1. Create a new Xcode project with iOS and macOS targets
2. Copy all the files listed above to your project
3. Ensure all files are added to both iOS and macOS targets
4. Configure the Info.plist with appropriate permissions
5. Add required frameworks
6. Build and test on both platforms

## File Dependencies

The files have the following dependencies:
- `SerialScannerView.swift` depends on `SerialScannerViewModel.swift`
- `SerialScannerViewModel.swift` depends on `AppleSerialValidator.swift` and `BackendService.swift`
- `SupportingViews.swift` depends on `BackendService.swift` and the Models
- All files use `PlatformDetector.swift` for platform detection

## Testing

After copying:
1. Test on iOS device/simulator
2. Test on macOS
3. Verify camera access works on both platforms
4. Test backend connectivity
5. Verify settings and history functionality

## Notes

- The app automatically adapts to the platform it's running on
- Camera functionality works on both iOS and macOS
- Flash control is only available on iOS
- All UI elements adapt appropriately for each platform
- Backend communication is identical across platforms
