# iOS Frontend Development Plan

## Overview
This document outlines the plan for developing the iOS frontend application for the Apple Serial Number OCR system. The iOS app will provide a native interface for capturing and processing images of Apple device serial numbers, communicating with our FastAPI backend for OCR processing.

## Project Structure

```
apple-ocr-ios-app/
├── .gitignore
├── README.md
├── AppleSerialOCR.xcodeproj/
├── AppleSerialOCR/
│   ├── Assets.xcassets/
│   ├── Info.plist
│   ├── AppleSerialOCRApp.swift
│   ├── Views/
│   │   ├── ContentView.swift
│   │   ├── ScannerView.swift
│   │   ├── ResultView.swift
│   │   ├── HistoryView.swift
│   │   ├── SettingsView.swift
│   │   └── Components/
│   │       ├── ROIOverlayView.swift
│   │       ├── DeviceTypeSelector.swift
│   │       ├── SerialCardView.swift
│   │       └── LoadingView.swift
│   ├── Models/
│   │   ├── SerialScanResult.swift
│   │   ├── DeviceType.swift
│   │   ├── ScanHistory.swift
│   │   └── AppSettings.swift
│   ├── Services/
│   │   ├── APIService.swift
│   │   ├── ImageProcessingService.swift
│   │   ├── HistoryService.swift
│   │   └── NetworkMonitor.swift
│   ├── Utils/
│   │   ├── ImageHelpers.swift
│   │   ├── SerialValidator.swift
│   │   └── Constants.swift
│   └── Resources/
│       ├── Localizable.strings
│       └── PresetDefinitions.json
└── AppleSerialOCRTests/
    └── SerialValidatorTests.swift
```

## Development Timeline

### Week 1: Foundation & Camera Integration

#### Day 1-2: Project Setup & UI Framework
- Create Xcode project with SwiftUI
- Set up navigation structure
- Implement basic UI components
- Configure camera permissions

#### Day 3-4: Camera & ROI Implementation
- Integrate VisionKit for camera access
- Implement ROI selection overlay
- Create image capture functionality
- Add device type selector UI

#### Day 5-7: API Integration
- Create API service for backend communication
- Implement image upload functionality
- Handle API responses and errors
- Add offline mode detection

### Week 2: Features & Polish

#### Day 8-9: Results & History
- Implement results display view
- Create history storage service
- Add history browsing functionality
- Implement export capabilities

#### Day 10-11: Settings & Configuration
- Add settings screen
- Implement server URL configuration
- Create preset management
- Add debug mode toggle

#### Day 12-14: Testing & Refinement
- Perform end-to-end testing
- Fix UI issues across devices
- Optimize performance
- Add final polish and animations

## Technical Implementation Details

### Camera & ROI Implementation

```swift
import SwiftUI
import VisionKit

struct ScannerView: View {
    @State private var showingImagePicker = false
    @State private var inputImage: UIImage?
    @State private var roiRect: CGRect = .zero
    @State private var selectedDeviceType: DeviceType = .macbook
    
    var body: some View {
        VStack {
            ZStack {
                CameraPreviewView()
                    .edgesIgnoringSafeArea(.all)
                
                ROIOverlayView(rect: $roiRect, deviceType: selectedDeviceType)
            }
            
            DeviceTypeSelector(selection: $selectedDeviceType)
            
            Button("Capture") {
                captureAndProcess()
            }
            .buttonStyle(.borderedProminent)
        }
    }
    
    func captureAndProcess() {
        guard let image = captureImageWithROI() else { return }
        
        // Get preset based on device type
        let preset = selectedDeviceType.apiPreset
        
        // Process with API
        APIService.shared.processImage(
            image: image,
            preset: preset,
            deviceType: selectedDeviceType.rawValue
        ) { result in
            switch result {
            case .success(let scanResult):
                // Handle successful scan
            case .failure(let error):
                // Handle error
            }
        }
    }
}
```

### API Service Implementation

```swift
import Foundation
import UIKit

class APIService {
    static let shared = APIService()
    
    private let baseURL: String
    
    init() {
        // Load from settings or use default
        self.baseURL = UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"
    }
    
    func processImage(image: UIImage, preset: String, deviceType: String, completion: @escaping (Result<SerialScanResult, Error>) -> Void) {
        // Prepare URL
        guard let url = URL(string: "\(baseURL)/process-serial") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        // Prepare multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        // Add query parameters
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "preset", value: preset),
            URLQueryItem(name: "device_type", value: deviceType)
        ]
        request.url = components.url
        
        // Create body
        request.httpBody = createBody(with: image, boundary: boundary)
        
        // Create task
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response
            // ...
        }
        
        task.resume()
    }
    
    private func createBody(with image: UIImage, boundary: String) -> Data {
        // Create multipart form data body
        // ...
    }
}
```

### ROI Overlay Implementation

```swift
import SwiftUI

struct ROIOverlayView: View {
    @Binding var rect: CGRect
    let deviceType: DeviceType
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Semi-transparent overlay
                Color.black.opacity(0.5)
                    .mask(
                        Rectangle()
                            .fill(Color.white)
                            .frame(width: geometry.size.width, height: geometry.size.height)
                            .overlay(
                                Rectangle()
                                    .fill(Color.black)
                                    .frame(width: rect.width, height: rect.height)
                                    .position(x: rect.midX, y: rect.midY)
                            )
                    )
                
                // ROI rectangle
                Rectangle()
                    .stroke(Color.yellow, lineWidth: 2)
                    .frame(width: rect.width, height: rect.height)
                    .position(x: rect.midX, y: rect.midY)
                
                // Drag handles
                // ...
            }
            .onAppear {
                // Set initial ROI based on device type
                setupInitialROI(in: geometry.size)
            }
        }
    }
    
    private func setupInitialROI(in size: CGSize) {
        // Set default ROI size based on device type
        let width = size.width * 0.8
        let aspectRatio: CGFloat
        
        switch deviceType {
        case .macbook, .imac:
            aspectRatio = 8.0 / 1.0  // Long and narrow for etched serials
        case .iphone, .ipad:
            aspectRatio = 5.0 / 1.0  // Medium ratio for screen serials
        case .accessory:
            aspectRatio = 4.0 / 1.0  // Shorter ratio for sticker serials
        }
        
        let height = width / aspectRatio
        
        // Center in view
        let x = (size.width - width) / 2
        let y = (size.height - height) / 2
        
        rect = CGRect(x: x, y: y, width: width, height: height)
    }
}
```

## Integration with Backend

### API Endpoints

The iOS app will communicate with the following backend endpoints:

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/process-serial` | POST | Upload image for OCR processing | `image` (multipart), `preset`, `device_type` |
| `/health` | GET | Check API status | None |
| `/params` | GET | Get available presets | None |

### Device Type to Preset Mapping

```swift
enum DeviceType: String, CaseIterable, Identifiable {
    case macbook = "MacBook"
    case imac = "iMac"
    case macmini = "Mac Mini"
    case iphone = "iPhone"
    case ipad = "iPad"
    case watch = "Apple Watch"
    case accessory = "Accessory"
    
    var id: String { self.rawValue }
    
    var apiPreset: String {
        switch self {
        case .macbook, .imac, .macmini:
            return "etched"
        case .iphone, .ipad:
            return "screen"
        case .watch, .accessory:
            return "sticker"
        }
    }
    
    var defaultROIAspectRatio: CGFloat {
        switch self {
        case .macbook, .imac, .macmini:
            return 8.0  // Long and narrow
        case .iphone, .ipad:
            return 5.0  // Medium
        case .watch, .accessory:
            return 4.0  // Shorter
        }
    }
}
```

## Offline Support

The app will implement basic offline support:

1. Cache the most recent successful API responses
2. Store captured images locally when offline
3. Attempt to reprocess stored images when connectivity is restored
4. Provide visual indication of offline status

## Error Handling

The app will handle the following error scenarios:

1. Network connectivity issues
2. API server errors
3. Image capture failures
4. Low confidence OCR results
5. Invalid serial numbers

Each error will have appropriate user feedback and recovery options.

## Testing Strategy

1. **Unit Tests**: Core business logic, validation, and data transformation
2. **Integration Tests**: API communication and response handling
3. **UI Tests**: Basic user flows and interactions
4. **Manual Testing**: Camera functionality and ROI selection

## Deployment Plan

1. **Development Build**: Internal testing on development devices
2. **TestFlight Beta**: Limited external testing with selected users
3. **App Store Release**: Public release after validation

## Resources and References

- [Live-Text-in-iOS-16](https://github.com/StewartLynch/Live-Text-in-iOS-16) - Reference implementation for text scanning
- [VisionKit Documentation](https://developer.apple.com/documentation/visionkit)
- Backend API Documentation: `http://localhost:8000/docs`
