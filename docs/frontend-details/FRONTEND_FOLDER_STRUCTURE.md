# iOS Frontend Folder Structure

This document outlines the complete folder structure for the Apple Serial OCR iOS application, including detailed descriptions of each component's purpose and functionality.

## Root Structure

```
apple-ocr-ios-app/
├── .gitignore                  # Git ignore file for Xcode and Swift
├── README.md                   # Project documentation
├── AppleSerialOCR.xcodeproj/   # Xcode project files
├── AppleSerialOCR.xcworkspace/ # Xcode workspace (if using CocoaPods)
├── Podfile                     # CocoaPods dependency file (if needed)
├── fastlane/                   # Fastlane configuration for CI/CD (optional)
└── AppleSerialOCR/             # Main application code
```

## Main Application Structure

```
AppleSerialOCR/
├── Info.plist                  # App configuration
├── AppleSerialOCRApp.swift     # SwiftUI app entry point
├── Assets.xcassets/            # Images and app icons
├── Preview Content/            # SwiftUI preview assets
├── Views/                      # UI components
├── Models/                     # Data models
├── Services/                   # Business logic and API services
├── Utils/                      # Helper functions and extensions
└── Resources/                  # Static resources and configuration
```

## Detailed Component Breakdown

### Views

```
Views/
├── ContentView.swift           # Main container view with tab navigation
├── ScannerView.swift           # Camera view with ROI selection
├── ResultView.swift            # OCR result display
├── HistoryView.swift           # Past scans history
├── SettingsView.swift          # App configuration
└── Components/                 # Reusable UI components
    ├── ROIOverlayView.swift    # Camera overlay for region selection
    ├── DeviceTypeSelector.swift # Device type selection UI
    ├── SerialCardView.swift    # Card view for displaying serial results
    ├── LoadingView.swift       # Loading indicator
    ├── ErrorView.swift         # Error display component
    └── ToastView.swift         # Toast notification component
```

### Models

```
Models/
├── SerialScanResult.swift      # OCR result model
├── DeviceType.swift            # Device type enumeration
├── ScanHistory.swift           # History storage model
├── AppSettings.swift           # User settings model
├── APIResponse.swift           # API response models
└── Errors/                     # Custom error types
    ├── APIError.swift          # Network and API errors
    ├── ScanError.swift         # Camera and scanning errors
    └── ValidationError.swift   # Serial validation errors
```

### Services

```
Services/
├── APIService.swift            # Backend API communication
├── ImageProcessingService.swift # Local image processing
├── HistoryService.swift        # Scan history management
├── NetworkMonitor.swift        # Network connectivity monitoring
├── SettingsService.swift       # User settings management
└── Analytics/                  # Optional analytics components
    ├── AnalyticsService.swift  # Analytics abstraction
    └── AnalyticsEvent.swift    # Analytics event definitions
```

### Utils

```
Utils/
├── ImageHelpers.swift          # Image manipulation utilities
├── SerialValidator.swift       # Serial number validation
├── Constants.swift             # App-wide constants
├── Logger.swift                # Structured logging
├── Extensions/                 # Swift extensions
│   ├── UIImage+Processing.swift # Image processing extensions
│   ├── String+Validation.swift # String validation extensions
│   └── View+Helpers.swift      # SwiftUI view extensions
└── Protocols/                  # Protocol definitions
    ├── ImageProcessor.swift    # Image processing protocol
    └── SerialDetector.swift    # Serial detection protocol
```

### Resources

```
Resources/
├── Localizable.strings         # Localization strings
├── PresetDefinitions.json      # OCR preset configurations
├── DeviceModels.json           # Apple device model information
└── Fonts/                      # Custom fonts (if needed)
```

## Test Structure

```
AppleSerialOCRTests/
├── UnitTests/
│   ├── Models/                 # Model tests
│   ├── Services/               # Service tests
│   └── Utils/                  # Utility tests
├── IntegrationTests/           # Integration tests
├── UITests/                    # UI automation tests
└── TestResources/              # Test images and mock data
    ├── MockResponses/          # Mock API responses
    └── TestImages/             # Test images for OCR
```

## Key Files Detailed

### App Entry Point

```swift
// AppleSerialOCRApp.swift
import SwiftUI

@main
struct AppleSerialOCRApp: App {
    @StateObject private var settingsService = SettingsService()
    @StateObject private var networkMonitor = NetworkMonitor()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(settingsService)
                .environmentObject(networkMonitor)
        }
    }
}
```

### Main Navigation

```swift
// ContentView.swift
import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @EnvironmentObject var networkMonitor: NetworkMonitor
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ScannerView()
                .tabItem {
                    Label("Scan", systemImage: "camera")
                }
                .tag(0)
            
            HistoryView()
                .tabItem {
                    Label("History", systemImage: "clock")
                }
                .tag(1)
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
        .overlay(
            Group {
                if !networkMonitor.isConnected {
                    VStack {
                        Text("Offline Mode")
                            .foregroundColor(.white)
                            .padding()
                            .background(Color.red)
                            .cornerRadius(8)
                        Spacer()
                    }
                    .padding(.top)
                }
            }
        )
    }
}
```

### Device Type Model

```swift
// DeviceType.swift
import Foundation

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
    
    var icon: String {
        switch self {
        case .macbook: return "laptopcomputer"
        case .imac: return "desktopcomputer"
        case .macmini: return "mac.mini"
        case .iphone: return "iphone"
        case .ipad: return "ipad"
        case .watch: return "applewatch"
        case .accessory: return "headphones"
        }
    }
    
    var defaultROIAspectRatio: CGFloat {
        switch self {
        case .macbook, .imac, .macmini:
            return 8.0  // Long and narrow for etched serials
        case .iphone, .ipad:
            return 5.0  // Medium ratio for screen serials
        case .watch, .accessory:
            return 4.0  // Shorter ratio for sticker serials
        }
    }
}
```

### API Service

```swift
// APIService.swift
import Foundation
import UIKit
import Combine

class APIService: ObservableObject {
    static let shared = APIService()
    
    @Published var isLoading = false
    
    private let baseURL: String
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        // Load from settings or use default
        self.baseURL = UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"
    }
    
    func processImage(image: UIImage, preset: String, deviceType: String) -> AnyPublisher<SerialScanResult, Error> {
        isLoading = true
        
        // Prepare URL
        guard let url = URL(string: "\(baseURL)/process-serial") else {
            return Fail(error: APIError.invalidURL).eraseToAnyPublisher()
        }
        
        // Add query parameters
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "preset", value: preset),
            URLQueryItem(name: "device_type", value: deviceType)
        ]
        
        guard let finalURL = components.url else {
            return Fail(error: APIError.invalidURL).eraseToAnyPublisher()
        }
        
        // Create multipart request
        var request = URLRequest(url: finalURL)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        // Create body
        guard let imageData = image.jpegData(compressionQuality: 0.8),
              let httpBody = createMultipartBody(with: imageData, boundary: boundary) else {
            return Fail(error: APIError.invalidData).eraseToAnyPublisher()
        }
        
        request.httpBody = httpBody
        
        // Create publisher
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: SerialScanResult.self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .handleEvents(receiveCompletion: { [weak self] _ in
                self?.isLoading = false
            })
            .eraseToAnyPublisher()
    }
    
    private func createMultipartBody(with imageData: Data, boundary: String) -> Data? {
        var body = Data()
        
        // Add image data
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        
        // Add closing boundary
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        
        return body
    }
}

enum APIError: Error {
    case invalidURL
    case invalidData
    case networkError
    case serverError(Int)
    case decodingError
}
```

### ROI Overlay View

```swift
// ROIOverlayView.swift
import SwiftUI

struct ROIOverlayView: View {
    @Binding var rect: CGRect
    let deviceType: DeviceType
    
    // Drag state
    @State private var dragOffset: CGSize = .zero
    @State private var isDragging = false
    
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
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                isDragging = true
                                let newX = rect.origin.x + value.translation.width - dragOffset.width
                                let newY = rect.origin.y + value.translation.height - dragOffset.height
                                
                                // Constrain to view bounds
                                let constrainedX = min(max(newX, 0), geometry.size.width - rect.width)
                                let constrainedY = min(max(newY, 0), geometry.size.height - rect.height)
                                
                                rect = CGRect(x: constrainedX, y: constrainedY, width: rect.width, height: rect.height)
                                dragOffset = value.translation
                            }
                            .onEnded { _ in
                                isDragging = false
                                dragOffset = .zero
                            }
                    )
                
                // Corner drag handles
                ForEach(0..<4) { corner in
                    let position = cornerPosition(for: corner, in: rect)
                    Circle()
                        .fill(Color.yellow)
                        .frame(width: 20, height: 20)
                        .position(position)
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    isDragging = true
                                    updateRect(for: corner, with: value.location, in: geometry.size)
                                }
                                .onEnded { _ in
                                    isDragging = false
                                }
                        )
                }
                
                // Guidance text
                VStack {
                    Spacer()
                    Text("Position the box around the serial number")
                        .foregroundColor(.white)
                        .padding()
                        .background(Color.black.opacity(0.7))
                        .cornerRadius(8)
                        .padding(.bottom, 20)
                }
            }
            .onAppear {
                // Set initial ROI based on device type
                setupInitialROI(in: geometry.size)
            }
        }
    }
    
    private func cornerPosition(for corner: Int, in rect: CGRect) -> CGPoint {
        switch corner {
        case 0: return CGPoint(x: rect.minX, y: rect.minY) // Top-left
        case 1: return CGPoint(x: rect.maxX, y: rect.minY) // Top-right
        case 2: return CGPoint(x: rect.maxX, y: rect.maxY) // Bottom-right
        case 3: return CGPoint(x: rect.minX, y: rect.maxY) // Bottom-left
        default: return .zero
        }
    }
    
    private func updateRect(for corner: Int, with location: CGPoint, in size: CGSize) {
        var newRect = rect
        
        switch corner {
        case 0: // Top-left
            newRect.origin.x = min(location.x, rect.maxX - 50)
            newRect.origin.y = min(location.y, rect.maxY - 20)
            newRect.size.width = rect.maxX - newRect.origin.x
            newRect.size.height = rect.maxY - newRect.origin.y
        case 1: // Top-right
            newRect.origin.y = min(location.y, rect.maxY - 20)
            newRect.size.width = max(location.x - rect.minX, 50)
            newRect.size.height = rect.maxY - newRect.origin.y
        case 2: // Bottom-right
            newRect.size.width = max(location.x - rect.minX, 50)
            newRect.size.height = max(location.y - rect.minY, 20)
        case 3: // Bottom-left
            newRect.origin.x = min(location.x, rect.maxX - 50)
            newRect.size.width = rect.maxX - newRect.origin.x
            newRect.size.height = max(location.y - rect.minY, 20)
        default:
            break
        }
        
        // Constrain to view bounds
        newRect.origin.x = max(0, newRect.origin.x)
        newRect.origin.y = max(0, newRect.origin.y)
        newRect.size.width = min(size.width - newRect.origin.x, newRect.size.width)
        newRect.size.height = min(size.height - newRect.origin.y, newRect.size.height)
        
        rect = newRect
    }
    
    private func setupInitialROI(in size: CGSize) {
        // Set default ROI size based on device type
        let width = size.width * 0.8
        let aspectRatio = deviceType.defaultROIAspectRatio
        let height = width / aspectRatio
        
        // Center in view
        let x = (size.width - width) / 2
        let y = (size.height - height) / 2
        
        rect = CGRect(x: x, y: y, width: width, height: height)
    }
}
```

## Integration with Backend

The iOS app will communicate with the backend API through the following key integration points:

1. **API Service**: Handles all communication with the backend
2. **Device Type to Preset Mapping**: Maps iOS device selections to backend presets
3. **ROI Selection**: Provides cropped images to improve OCR accuracy
4. **Error Handling**: Manages API errors and provides appropriate user feedback

## Build Configuration

The project will include the following build configurations:

1. **Debug**: Development environment with local backend
2. **Staging**: Testing environment with staging backend
3. **Release**: Production environment with production backend

Each configuration will have appropriate API endpoints and logging levels defined in the `Info.plist` file.

## Dependencies

The project will use the following external dependencies:

1. **Alamofire** (optional): For advanced networking capabilities
2. **Kingfisher** (optional): For image caching and processing
3. **SwiftUI-Introspect**: For advanced SwiftUI customization

These dependencies can be managed using Swift Package Manager or CocoaPods.

## Deployment Target

- iOS 16.0 and above (required for VisionKit DataScannerViewController)
- Compatible with iPhone and iPad
- Optimized for iOS 17 with latest SwiftUI features
