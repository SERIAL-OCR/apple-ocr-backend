# Xcode Project Setup Guide

## Overview
This guide provides step-by-step instructions for setting up the Apple Serial Scanner Xcode project with both iOS and macOS targets, using our existing Swift implementation.

## Prerequisites
- Xcode 15.0 or later
- macOS 14.0 or later
- iOS 17.0+ target devices
- Apple Developer Account (for device testing)

## Step 1: Create New Xcode Project

### 1.1 Create iOS App
1. Open Xcode
2. File → New → Project
3. Select **iOS** → **App**
4. Configure project:
   - **Product Name:** `AppleSerialScanner`
   - **Team:** Your development team
   - **Organization Identifier:** `com.yourcompany` (e.g., `com.appleocr`)
   - **Interface:** `SwiftUI`
   - **Language:** `Swift`
   - **Use Core Data:** `No`
   - **Include Tests:** `No`
5. Choose project location and click **Create**

### 1.2 Add macOS Target
1. File → New → Target
2. Select **macOS** → **App**
3. Configure target:
   - **Product Name:** `AppleSerialScanner`
   - **Interface:** `SwiftUI`
   - **Language:** `Swift`
   - **Use Core Data:** `No`
   - **Include Tests:** `No`
4. Click **Finish**

## Step 2: Project Structure Setup

### 2.1 Create Folder Structure
In Xcode Project Navigator, create the following folder structure:

```
AppleSerialScanner/
├── Views/
├── Services/
├── Utils/
├── Models/
└── Supporting Files/
```

**Steps:**
1. Right-click on project root → New Group
2. Name each group as shown above
3. Move existing files to appropriate groups

### 2.2 Update Target Membership
1. Select each Swift file
2. In File Inspector (right panel), check both iOS and macOS targets
3. Ensure all files are included in both targets

## Step 3: Copy Implementation Files

### 3.1 Copy from Our Implementation
Copy the following files from `ios/AppleSerialScanner/AppleSerialScanner/` to your Xcode project:

**Main App Files:**
- `AppleSerialScannerApp.swift` → Replace existing app file
- `SerialScannerView.swift` → Views/
- `SerialScannerViewModel.swift` → Views/

**Supporting Views:**
- `SupportingViews.swift` → Views/

**Services:**
- `BackendService.swift` → Services/

**Models:**
- `Models/SerialSubmission.swift` → Models/
- `Models/SerialResponse.swift` → Models/
- `Models/ScanHistory.swift` → Models/
- `Models/SystemStats.swift` → Models/

**Utils:**
- `Utils/PlatformDetector.swift` → Utils/
- `Utils/CameraManager.swift` → Utils/
- `AppleSerialValidator.swift` → Utils/

### 3.2 File Copy Process
1. **For each file:**
   - Right-click target group → Add Files to "AppleSerialScanner"
   - Select the file from our implementation
   - Ensure "Add to targets" includes both iOS and macOS
   - Click "Add"

2. **Replace existing files:**
   - Delete existing `ContentView.swift` and `AppleSerialScannerApp.swift`
   - Add our implementation files

## Step 4: Configure Info.plist

### 4.1 iOS Info.plist
Add the following keys to iOS target's Info.plist:

```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to scan Apple device serial numbers.</string>
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access for video capture.</string>
```

### 4.2 macOS Info.plist
Add the following keys to macOS target's Info.plist:

```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to scan Apple device serial numbers.</string>
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access for video capture.</string>
```

## Step 5: Configure Build Settings

### 5.1 iOS Target Settings
1. Select iOS target
2. Build Settings tab
3. Configure:
   - **Deployment Target:** iOS 17.0
   - **Swift Language Version:** Swift 5
   - **Enable Bitcode:** No

### 5.2 macOS Target Settings
1. Select macOS target
2. Build Settings tab
3. Configure:
   - **Deployment Target:** macOS 14.0
   - **Swift Language Version:** Swift 5
   - **Enable Bitcode:** No

## Step 6: Add Required Frameworks

### 6.1 iOS Target
1. Select iOS target
2. General tab → Frameworks, Libraries, and Embedded Content
3. Click + and add:
   - `AVFoundation.framework`
   - `Vision.framework`
   - `CoreImage.framework`

### 6.2 macOS Target
1. Select macOS target
2. General tab → Frameworks, Libraries, and Embedded Content
3. Click + and add:
   - `AVFoundation.framework`
   - `Vision.framework`
   - `CoreImage.framework`

## Step 7: Configure Signing & Capabilities

### 7.1 iOS Target
1. Select iOS target
2. Signing & Capabilities tab
3. Configure:
   - **Team:** Your development team
   - **Bundle Identifier:** `com.yourcompany.AppleSerialScanner`
   - **Automatically manage signing:** Checked

### 7.2 macOS Target
1. Select macOS target
2. Signing & Capabilities tab
3. Configure:
   - **Team:** Your development team
   - **Bundle Identifier:** `com.yourcompany.AppleSerialScanner-macOS`
   - **Automatically manage signing:** Checked

## Step 8: Test Build

### 8.1 iOS Build Test
1. Select iOS target
2. Choose iOS Simulator (iPhone 15 Pro)
3. Product → Build (⌘B)
4. Verify no build errors

### 8.2 macOS Build Test
1. Select macOS target
2. Choose Mac target
3. Product → Build (⌘B)
4. Verify no build errors

## Step 9: Configure Backend Connection

### 9.1 Update Backend URL
In `BackendService.swift`, update the default backend URL:

```swift
// Update this line in BackendService.swift
private let defaultBaseURL = "http://localhost:8000"
```

### 9.2 Test Backend Connection
1. Ensure backend server is running
2. Run app on device/simulator
3. Go to Settings tab
4. Test connection to backend

## Step 10: Device Testing Setup

### 10.1 iOS Device Testing
1. Connect iOS device via USB
2. Trust computer on device
3. Select device in Xcode scheme
4. Product → Run (⌘R)

### 10.2 macOS Testing
1. Select macOS target
2. Product → Run (⌘R)
3. Grant camera permissions when prompted

## Troubleshooting

### Common Issues

#### Build Errors
1. **Missing frameworks:** Ensure all required frameworks are added
2. **Swift version conflicts:** Verify Swift 5 is selected
3. **Target membership:** Check all files are included in both targets

#### Runtime Errors
1. **Camera permissions:** Verify Info.plist keys are correct
2. **Backend connection:** Check server is running and URL is correct
3. **Platform detection:** Verify PlatformDetector.swift is working

#### Device Issues
1. **Signing errors:** Check team and bundle identifier
2. **Permission denied:** Grant camera permissions in Settings
3. **Network issues:** Verify device can reach backend server

### Debug Tips
1. **Console logs:** Check Xcode console for errors
2. **Breakpoints:** Set breakpoints in key functions
3. **Simulator testing:** Test on simulator first, then device
4. **Clean build:** Product → Clean Build Folder (⇧⌘K)

## Next Steps

### After Successful Setup
1. **Run smoke tests:** Follow `SMOKE_TESTING_GUIDE.md`
2. **Test all features:** Camera, validation, submission, export
3. **Performance testing:** Verify 2-4 second scan times
4. **Cross-platform testing:** Ensure iOS and macOS work consistently

### Production Preparation
1. **Code signing:** Configure production certificates
2. **App Store preparation:** Create app store listings
3. **Distribution:** Set up TestFlight or direct distribution
4. **Documentation:** Create user guides and support materials

## File Structure Reference

```
AppleSerialScanner.xcodeproj/
├── AppleSerialScanner/
│   ├── Views/
│   │   ├── SerialScannerView.swift
│   │   ├── SerialScannerViewModel.swift
│   │   └── SupportingViews.swift
│   ├── Services/
│   │   └── BackendService.swift
│   ├── Utils/
│   │   ├── PlatformDetector.swift
│   │   ├── CameraManager.swift
│   │   └── AppleSerialValidator.swift
│   ├── Models/
│   │   ├── SerialSubmission.swift
│   │   ├── SerialResponse.swift
│   │   ├── ScanHistory.swift
│   │   └── SystemStats.swift
│   ├── Supporting Files/
│   │   ├── Info.plist (iOS)
│   │   └── Info.plist (macOS)
│   └── AppleSerialScannerApp.swift
└── AppleSerialScanner-macOS/
    └── (Same structure as iOS)
```

This setup creates a unified Xcode project with both iOS and macOS targets sharing the same codebase, using platform detection to handle platform-specific differences.
