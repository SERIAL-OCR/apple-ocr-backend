# Day 6: iOS Frontend Integration Plan

## 🎯 Overview

This document outlines our Day 6 plan for integrating the iOS frontend with our enhanced OCR backend. Building on the improvements from Day 5, we'll focus on creating a seamless user experience that leverages the backend's progressive processing, device-specific presets, and advanced OCR capabilities.

## 📋 Integration Tasks

### Phase 1: Core API Integration (Priority High)

1. **API Service Implementation**
   - Create enhanced `APIService` class with proper error handling
   - Implement multipart form data upload for images
   - Add support for device-specific presets
   - Implement connection monitoring and retry logic

2. **Progressive Processing Support**
   - Add timeout parameters for progressive processing
   - Implement loading indicators with progress feedback
   - Create fallback mechanisms for slow processing

3. **Device Type Mapping**
   - Map iOS device types to backend presets
   - Implement auto-detection of current device
   - Allow manual override of device type

### Phase 2: Camera & ROI Integration (Priority High)

1. **Camera Integration**
   - Implement VisionKit camera access
   - Add photo library picker as alternative
   - Support both landscape and portrait orientations

2. **ROI Selection**
   - Create adjustable ROI overlay based on device type
   - Implement device-specific aspect ratios
   - Add visual guides for proper serial positioning
   - Implement ROI cropping before API submission

3. **Image Processing**
   - Add basic image enhancement before upload
   - Implement image rotation detection
   - Support for multiple image formats

### Phase 3: Results & History (Priority Medium)

1. **Results Display**
   - Create result view with confidence indicators
   - Implement validation visualization
   - Add copy/share functionality
   - Show debug images when in debug mode

2. **History Management**
   - Implement local storage for scan history
   - Add filtering and sorting options
   - Create history detail view
   - Implement export functionality

### Phase 4: Settings & Configuration (Priority Medium)

1. **Settings Interface**
   - Create settings view with server configuration
   - Add debug mode toggle
   - Implement theme and appearance options
   - Add about/help section

2. **Advanced Options**
   - Create advanced OCR parameter controls
   - Add manual preset selection
   - Implement custom timeout controls
   - Create debug logging options

### Phase 5: Testing & Refinement (Priority High)

1. **Integration Testing**
   - Test all API endpoints with real backend
   - Verify error handling and recovery
   - Test offline functionality
   - Validate all device type presets

2. **Performance Optimization**
   - Optimize image processing for speed
   - Reduce memory usage
   - Implement caching for faster repeat scans
   - Optimize UI responsiveness during processing

## 🔄 API Integration Details

### Endpoints to Implement

| Endpoint | Method | Purpose | Parameters |
|----------|--------|---------|------------|
| `/process-serial` | POST | Main OCR processing | `image`, `device_type`, `preset`, `use_progressive` |
| `/health` | GET | Server status check | None |
| `/params` | GET | Retrieve available presets | `preset` (optional) |

### Request Example

```swift
func processImage(image: UIImage, deviceType: DeviceType) {
    // Prepare multipart form data
    let formData = MultipartFormData()
    
    // Add image data
    if let imageData = image.jpegData(compressionQuality: 0.8) {
        formData.append(imageData, withName: "image", fileName: "image.jpg", mimeType: "image/jpeg")
    }
    
    // Add parameters
    let parameters = [
        "device_type": deviceType.rawValue,
        "preset": deviceType.apiPreset,
        "use_progressive": "true",
        "early_stop_confidence": "0.85",
        "max_processing_time": "30.0"
    ]
    
    // Send request
    apiService.sendRequest(
        endpoint: "/process-serial",
        method: .post,
        formData: formData,
        parameters: parameters
    ) { result in
        switch result {
        case .success(let response):
            // Handle successful response
            handleOCRResult(response)
        case .failure(let error):
            // Handle error
            handleAPIError(error)
        }
    }
}
```

### Response Handling

```swift
func handleOCRResult(_ response: APIResponse<SerialScanResult>) {
    // Extract serial number results
    guard let serials = response.data?.serials, !serials.isEmpty else {
        // No results found
        showNoResultsMessage()
        return
    }
    
    // Get top result
    let topResult = serials[0]
    
    // Update UI
    DispatchQueue.main.async {
        self.resultView.serialNumber = topResult.serial
        self.resultView.confidence = topResult.confidence
        self.resultView.validationStatus = validateSerial(topResult.serial)
        
        // Save to history
        historyService.addScan(topResult)
        
        // Show debug image if available
        if let debugPath = response.debug, isDebugMode {
            loadDebugImage(from: debugPath)
        }
    }
}
```

## 📱 UI Components to Implement

### 1. Camera View with ROI Overlay

```swift
struct ScannerView: View {
    @State private var roiRect: CGRect = .zero
    @State private var selectedDeviceType: DeviceType = .macbook
    @State private var isProcessing = false
    @State private var showingImagePicker = false
    
    var body: some View {
        ZStack {
            // Camera preview
            CameraPreviewView()
                .edgesIgnoringSafeArea(.all)
            
            // ROI overlay with device-specific aspect ratio
            ROIOverlayView(
                rect: $roiRect,
                deviceType: selectedDeviceType,
                isProcessing: isProcessing
            )
            
            VStack {
                Spacer()
                
                // Device type selector
                DeviceTypeSelector(selection: $selectedDeviceType)
                    .padding()
                
                // Capture button
                Button(action: captureAndProcess) {
                    Label("Capture", systemImage: "camera")
                        .font(.headline)
                        .padding()
                        .background(Capsule().fill(Color.accentColor))
                        .foregroundColor(.white)
                }
                .disabled(isProcessing)
                .padding(.bottom)
                
                // Photo library button
                Button(action: { showingImagePicker = true }) {
                    Label("Photo Library", systemImage: "photo")
                }
                .padding(.bottom)
            }
            
            // Loading overlay
            if isProcessing {
                LoadingView(message: "Processing image...")
            }
        }
        .sheet(isPresented: $showingImagePicker) {
            ImagePicker(selectedImage: $inputImage)
        }
    }
    
    func captureAndProcess() {
        guard let croppedImage = captureImageWithROI() else { return }
        isProcessing = true
        
        apiService.processImage(
            image: croppedImage,
            deviceType: selectedDeviceType
        ) { result in
            isProcessing = false
            // Handle result...
        }
    }
}
```

### 2. Results View

```swift
struct ResultView: View {
    let scanResult: SerialScanResult
    @State private var showingShareSheet = false
    
    var body: some View {
        VStack(spacing: 20) {
            // Serial number display
            Text(scanResult.serialNumber)
                .font(.system(.title, design: .monospaced))
                .fontWeight(.bold)
            
            // Confidence indicator
            ConfidenceIndicator(value: scanResult.confidence)
            
            // Details
            VStack(alignment: .leading, spacing: 12) {
                DetailRow(label: "Device Type", value: scanResult.deviceType.displayName)
                DetailRow(label: "Confidence", value: "\(Int(scanResult.confidence * 100))%")
                DetailRow(label: "Processing Time", value: "\(scanResult.processingTime, specifier: "%.2f")s")
                DetailRow(label: "Timestamp", value: formattedDate(scanResult.timestamp))
                DetailRow(label: "Validation", value: validationStatusText)
            }
            .padding()
            .background(RoundedRectangle(cornerRadius: 12).fill(Color(.systemBackground)))
            .shadow(radius: 2)
            
            // Action buttons
            HStack(spacing: 30) {
                Button(action: copyToClipboard) {
                    Label("Copy", systemImage: "doc.on.doc")
                }
                
                Button(action: { showingShareSheet = true }) {
                    Label("Share", systemImage: "square.and.arrow.up")
                }
                
                Button(action: saveToHistory) {
                    Label("Save", systemImage: "square.and.arrow.down")
                }
            }
            .padding()
        }
        .padding()
        .sheet(isPresented: $showingShareSheet) {
            ShareSheet(items: [scanResult.serialNumber])
        }
    }
}
```

## 🧪 Testing Strategy

1. **Unit Tests**
   - Test API request/response parsing
   - Test device type to preset mapping
   - Test serial number validation

2. **Integration Tests**
   - Test API communication with mock server
   - Test image processing pipeline
   - Test error handling and recovery

3. **UI Tests**
   - Test camera and ROI interaction
   - Test navigation flow
   - Test settings persistence

4. **Manual Testing**
   - Test with real Apple devices
   - Test in various lighting conditions
   - Test with damaged/worn serials

## 📅 Implementation Timeline

### Day 6 Morning (4 hours)
- Set up API service and models
- Implement camera and ROI integration
- Create basic results display

### Day 6 Afternoon (4 hours)
- Complete device type mapping
- Implement history storage
- Add settings interface
- Begin integration testing

### Day 7 Morning (4 hours)
- Fix integration issues
- Optimize performance
- Enhance error handling
- Complete UI refinements

### Day 7 Afternoon (4 hours)
- Comprehensive testing
- Documentation
- Final polish and bug fixes
- Prepare for demo/handoff

## 🚀 Getting Started

1. Clone the repository
2. Open `AppleSerialOCR.xcodeproj` in Xcode
3. Install dependencies (if using CocoaPods/SPM)
4. Configure backend URL in `Constants.swift`
5. Build and run on a device with camera

## 🔗 Dependencies

- **SwiftUI**: UI framework
- **Combine**: Reactive programming
- **VisionKit**: Camera and text recognition
- **PhotosUI**: Photo library access
- **URLSession**: Networking
- **CoreData**: Local storage

## 📝 Conclusion

This integration plan provides a comprehensive roadmap for connecting our iOS frontend with the enhanced OCR backend. By focusing on progressive implementation and thorough testing, we'll create a robust, user-friendly application that leverages the full capabilities of our backend system.
