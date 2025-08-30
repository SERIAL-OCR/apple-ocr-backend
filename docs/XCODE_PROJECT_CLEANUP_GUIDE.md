# Xcode Project Cleanup Guide

## Overview
This guide will help you clean up your Xcode project by removing the default boilerplate files and replacing them with our Apple Serial Scanner implementation.

## Step 1: Remove Boilerplate Files

In your Xcode project, delete these default files:
- `ContentView.swift` (default SwiftUI view)
- `ContentView_Previews.swift` (preview file)
- Any other default template files

## Step 2: Update Project Structure

Your project should have this structure:
```
AppleSerialScanner.xcodeproj/
└── AppleSerialScanner/
    ├── AppleSerialScannerApp.swift
    ├── Info.plist
    ├── SerialScannerView.swift
    ├── SerialScannerViewModel.swift
    ├── SupportingViews.swift
    ├── AppleSerialValidator.swift
    ├── BackendService.swift
    ├── Models/
    │   ├── SerialSubmission.swift
    │   ├── SerialResponse.swift
    │   ├── ScanHistory.swift
    │   └── SystemStats.swift
    └── Utils/
        ├── CameraManager.swift
        └── PlatformDetector.swift
```

## Step 3: Configure Target Settings

### General Tab
- **Display Name**: Apple Serial Scanner
- **Bundle Identifier**: com.yourcompany.appleserialscanner
- **Version**: 1.0
- **Build**: 1

### Deployment Info
- **iOS Deployment Target**: 15.0
- **macOS Deployment Target**: 12.0
- **Devices**: iPhone, iPad, Mac

### Supported Destinations
- ✅ iPhone
- ✅ iPad  
- ✅ Mac

## Step 4: Add Required Frameworks

In your target's "Frameworks, Libraries, and Embedded Content" section, add:
- `Vision.framework`
- `VisionKit.framework` (iOS only)
- `AVFoundation.framework`
- `SwiftUI.framework`

## Step 5: Configure Info.plist

Replace the default Info.plist content with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>$(DEVELOPMENT_LANGUAGE)</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$(PRODUCT_NAME)</string>
    <key>CFBundlePackageType</key>
    <string>$(PRODUCT_BUNDLE_PACKAGE_TYPE)</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>NSCameraUsageDescription</key>
    <string>This app needs camera access to scan Apple serial numbers.</string>
    <key>UIApplicationSceneManifest</key>
    <dict>
        <key>UIApplicationSupportsMultipleScenes</key>
        <true/>
        <key>UISceneConfigurations</key>
        <dict>
            <key>UIWindowSceneSessionRoleApplication</key>
            <array>
                <dict>
                    <key>UISceneConfigurationName</key>
                    <string>Default Configuration</string>
                    <key>UISceneDelegateClassName</key>
                    <string>$(PRODUCT_MODULE_NAME).SceneDelegate</string>
                </dict>
            </array>
        </dict>
    </dict>
    <key>UILaunchScreen</key>
    <dict/>
    <key>UIRequiredDeviceCapabilities</key>
    <array>
        <string>armv7</string>
    </array>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UISupportedInterfaceOrientations~ipad</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationPortraitUpsideDown</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
</dict>
</plist>
```

## Step 6: Update AppleSerialScannerApp.swift

Make sure your `AppleSerialScannerApp.swift` contains:

```swift
import SwiftUI

@main
struct AppleSerialScannerApp: App {
    var body: some Scene {
        WindowGroup {
            SerialScannerView()
        }
    }
}
```

## Step 7: Build Settings

### Swift Compiler - Language
- **Swift Language Version**: Swift 5.0

### Architectures
- **Architectures**: $(ARCHS_STANDARD)
- **Valid Architectures**: arm64, x86_64

### Deployment
- **iOS Deployment Target**: 15.0
- **macOS Deployment Target**: 12.0

## Step 8: Test the Build

1. **Clean Build Folder**: Product → Clean Build Folder
2. **Build for iOS**: Select iOS Simulator and build
3. **Build for macOS**: Select Mac and build
4. **Fix any compilation errors** that appear

## Common Issues and Solutions

### Issue: "Cannot find 'SerialScannerView' in scope"
**Solution**: Make sure `SerialScannerView.swift` is added to your target

### Issue: "Missing required capability"
**Solution**: Add camera usage description to Info.plist

### Issue: "Framework not found"
**Solution**: Add required frameworks in target settings

### Issue: "Platform not supported"
**Solution**: Check deployment targets and supported destinations

## Step 9: Verify All Files Are Present

Run this command in terminal to verify all files exist:
```bash
find ios/AppleSerialScanner/AppleSerialScanner -name "*.swift" -o -name "*.plist"
```

You should see:
- AppleSerialScannerApp.swift
- SerialScannerView.swift
- SerialScannerViewModel.swift
- SupportingViews.swift
- AppleSerialValidator.swift
- BackendService.swift
- Info.plist
- Models/SerialSubmission.swift
- Models/SerialResponse.swift
- Models/ScanHistory.swift
- Models/SystemStats.swift
- Utils/CameraManager.swift
- Utils/PlatformDetector.swift

## Step 10: Final Verification

1. **iOS Build**: Should compile and run on iOS simulator
2. **macOS Build**: Should compile and run on Mac
3. **Camera Access**: Should request camera permission
4. **UI Elements**: Should show appropriate platform-specific elements

## Next Steps

After successful cleanup:
1. Test camera functionality on both platforms
2. Configure backend URL in Settings
3. Test serial number scanning
4. Verify history and export functionality
