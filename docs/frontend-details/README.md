# Apple OCR iOS Frontend Documentation

## Overview

This directory contains comprehensive documentation for the Apple OCR iOS frontend application. The iOS app is designed to work with the Apple OCR backend service to capture and process Apple device serial numbers using the device camera.

## Documentation Index

### Planning & Architecture
- [**PROJECT_OVERVIEW.md**](PROJECT_OVERVIEW.md) - High-level overview of the frontend project
- [**IOS_FRONTEND_PLAN.md**](IOS_FRONTEND_PLAN.md) - Detailed development plan and timeline
- [**FRONTEND_FOLDER_STRUCTURE.md**](FRONTEND_FOLDER_STRUCTURE.md) - Complete folder structure with component descriptions

### Integration & Technical Guides
- [**BACKEND_INTEGRATION_GUIDE.md**](BACKEND_INTEGRATION_GUIDE.md) - Guide for integrating with the backend API
- [**APPLE_SILICON_INTEGRATION.md**](APPLE_SILICON_INTEGRATION.md) - Guide for GPU acceleration on Apple Silicon

### Project Context
- [**PROJECT_CONTEXT.md**](PROJECT_CONTEXT.md) - Background information and project context
- [**DEVELOPMENT_JOURNAL.md**](DEVELOPMENT_JOURNAL.md) - Development progress and decision log

## Key Features

The iOS frontend application includes the following key features:

1. **Camera Integration with ROI Selection**
   - Native camera integration using VisionKit
   - Custom Region of Interest (ROI) selection overlay
   - Automatic ROI aspect ratio adjustment based on device type

2. **Device Type Selection**
   - Support for multiple Apple device types (MacBook, iMac, iPhone, etc.)
   - Automatic preset selection based on device type

3. **OCR Processing**
   - Integration with backend OCR service
   - Support for multiple processing presets
   - Handling of low-confidence results

4. **History and Export**
   - Local storage of scan history
   - Export options (CSV, Excel)
   - Image caching for offline review

5. **Settings and Configuration**
   - Backend server configuration
   - Default device type preferences
   - Debug mode for developers

## Getting Started

To start developing the iOS frontend:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/apple-ocr-ios-app.git
   cd apple-ocr-ios-app
   ```

2. Open the project in Xcode:
   ```bash
   open AppleSerialOCR.xcodeproj
   ```

3. Install dependencies (if using Swift Package Manager):
   - In Xcode, go to File > Swift Packages > Resolve Package Versions

4. Build and run the project:
   - Select a simulator or connected device
   - Click the Run button or press Cmd+R

## Development Requirements

- Xcode 14.0 or later
- iOS 16.0+ deployment target
- Swift 5.7 or later
- macOS 12.0+ for development
- Apple Developer account for testing on physical devices

## Backend Integration

The iOS app communicates with the backend service through a RESTful API. Key endpoints include:

- `POST /process-serial` - Upload image for OCR processing
- `GET /health` - Check API status
- `GET /params` - Get available presets

For detailed integration information, see [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md).

## Project Structure

The iOS app follows the MVVM (Model-View-ViewModel) architecture pattern with SwiftUI as the primary UI framework. The project is organized into the following main components:

- **Views**: SwiftUI views for user interface
- **Models**: Data structures for application state
- **Services**: Business logic and API communication
- **Utils**: Helper functions and extensions

For a complete folder structure, see [FRONTEND_FOLDER_STRUCTURE.md](FRONTEND_FOLDER_STRUCTURE.md).

## Contributing

When contributing to the iOS frontend:

1. Follow the established architecture and coding patterns
2. Maintain SwiftUI best practices
3. Write unit tests for new functionality
4. Update documentation as needed

## Resources

- [Apple VisionKit Documentation](https://developer.apple.com/documentation/visionkit)
- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui)
- [Backend API Documentation](http://localhost:8000/docs)
- [Live-Text-in-iOS-16](https://github.com/StewartLynch/Live-Text-in-iOS-16) - Reference implementation
