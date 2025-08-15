# Backend Integration Guide for iOS Frontend

This guide details how the iOS frontend application integrates with the Apple OCR backend service, including API endpoints, data formats, and implementation patterns.

## API Endpoints

The iOS app communicates with the following backend endpoints:

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/process-serial` | POST | Upload image for OCR processing | `image` (multipart), `preset`, `device_type` |
| `/health` | GET | Check API status | None |
| `/params` | GET | Get available presets | None |
| `/evaluate` | GET | Run evaluation on test images | `dir`, `preset` |
| `/export` | GET | Download Excel report | None |

## Authentication

Currently, the API uses a simple API key authentication mechanism:

```swift
// Add API key to requests
var request = URLRequest(url: url)
request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
```

## Image Upload

Images are sent to the backend using multipart/form-data:

```swift
func uploadImage(image: UIImage, preset: String, deviceType: String) -> AnyPublisher<SerialScanResult, Error> {
    // Prepare URL with query parameters
    var components = URLComponents(url: baseURL.appendingPathComponent("process-serial"), resolvingAgainstBaseURL: true)!
    components.queryItems = [
        URLQueryItem(name: "preset", value: preset),
        URLQueryItem(name: "device_type", value: deviceType)
    ]
    
    guard let url = components.url else {
        return Fail(error: APIError.invalidURL).eraseToAnyPublisher()
    }
    
    // Create multipart request
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    // Create body with image data
    guard let imageData = image.jpegData(compressionQuality: 0.8) else {
        return Fail(error: APIError.invalidData).eraseToAnyPublisher()
    }
    
    var body = Data()
    
    // Add image part
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(imageData)
    body.append("\r\n".data(using: .utf8)!)
    
    // Close boundary
    body.append("--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    // Send request
    return URLSession.shared.dataTaskPublisher(for: request)
        .map(\.data)
        .decode(type: SerialScanResult.self, decoder: JSONDecoder())
        .receive(on: DispatchQueue.main)
        .eraseToAnyPublisher()
}
```

## Response Handling

### Successful Response

```json
{
  "serial": "C02XL0THJHCC",
  "confidence": 0.95,
  "device_type": "MacBook Pro",
  "is_valid": true,
  "debug_image_path": "/tmp/ocr_debug_123456.jpg"
}
```

### Error Response

```json
{
  "detail": "Error processing image: No text detected",
  "error_code": "NO_TEXT_DETECTED",
  "status_code": 422
}
```

## Implementation in iOS App

### API Service

```swift
class APIService {
    static let shared = APIService()
    private let baseURL: URL
    
    init() {
        // Load from settings or use default
        let urlString = UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"
        self.baseURL = URL(string: urlString)!
    }
    
    // Process serial image
    func processSerial(image: UIImage, preset: String, deviceType: String) -> AnyPublisher<SerialScanResult, Error> {
        return uploadImage(image: image, preset: preset, deviceType: deviceType)
    }
    
    // Check API health
    func checkHealth() -> AnyPublisher<HealthStatus, Error> {
        let request = URLRequest(url: baseURL.appendingPathComponent("health"))
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: HealthStatus.self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
    
    // Get available presets
    func getPresets() -> AnyPublisher<PresetsResponse, Error> {
        let request = URLRequest(url: baseURL.appendingPathComponent("params"))
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: PresetsResponse.self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
}
```

### Model Definitions

```swift
// Serial scan result
struct SerialScanResult: Codable {
    let serial: String
    let confidence: Double
    let deviceType: String?
    let isValid: Bool
    let debugImagePath: String?
    
    enum CodingKeys: String, CodingKey {
        case serial
        case confidence
        case deviceType = "device_type"
        case isValid = "is_valid"
        case debugImagePath = "debug_image_path"
    }
}

// API error
struct APIErrorResponse: Codable {
    let detail: String
    let errorCode: String
    let statusCode: Int
    
    enum CodingKeys: String, CodingKey {
        case detail
        case errorCode = "error_code"
        case statusCode = "status_code"
    }
}

// Health status
struct HealthStatus: Codable {
    let status: String
    let version: String
    let gpuAvailable: Bool
    
    enum CodingKeys: String, CodingKey {
        case status
        case version
        case gpuAvailable = "gpu_available"
    }
}

// Presets response
struct PresetsResponse: Codable {
    let presets: [String: PresetConfig]
}

struct PresetConfig: Codable {
    let description: String
    let parameters: [String: AnyCodable]
}
```

## Device Type to Preset Mapping

The iOS app maps device types to backend presets:

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
}
```

## Error Handling

The app handles various error scenarios from the API:

```swift
enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidData
    case networkError
    case serverError(Int, String)
    case decodingError
    case noTextDetected
    case lowConfidence
    case timeout
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidData:
            return "Invalid data"
        case .networkError:
            return "Network error"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        case .decodingError:
            return "Error decoding response"
        case .noTextDetected:
            return "No text detected in image"
        case .lowConfidence:
            return "Low confidence in detected text"
        case .timeout:
            return "Request timed out"
        }
    }
}

// Error handling in API calls
func handleAPIError(_ error: Error) -> APIError {
    if let urlError = error as? URLError {
        switch urlError.code {
        case .timedOut:
            return .timeout
        default:
            return .networkError
        }
    } else if let apiError = error as? APIError {
        return apiError
    } else {
        return .serverError(0, error.localizedDescription)
    }
}
```

## Offline Mode

The app implements basic offline support:

```swift
class NetworkMonitor: ObservableObject {
    @Published var isConnected = true
    private let monitor = NWPathMonitor()
    
    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
            }
        }
        let queue = DispatchQueue(label: "NetworkMonitor")
        monitor.start(queue: queue)
    }
    
    deinit {
        monitor.cancel()
    }
}

// Usage in API service
func processSerial(image: UIImage, preset: String, deviceType: String) -> AnyPublisher<SerialScanResult, Error> {
    guard NetworkMonitor.shared.isConnected else {
        // Save image for later processing
        let savedImagePath = saveImageForLaterProcessing(image, preset: preset, deviceType: deviceType)
        return Fail(error: APIError.networkError).eraseToAnyPublisher()
    }
    
    return uploadImage(image: image, preset: preset, deviceType: deviceType)
}

// Process pending offline images
func processPendingImages() {
    guard NetworkMonitor.shared.isConnected else { return }
    
    let pendingImages = loadPendingImages()
    for pendingImage in pendingImages {
        processSerial(
            image: pendingImage.image,
            preset: pendingImage.preset,
            deviceType: pendingImage.deviceType
        )
        .sink(
            receiveCompletion: { _ in },
            receiveValue: { result in
                // Handle result
            }
        )
        .store(in: &cancellables)
    }
}
```

## Configuration Management

The app allows users to configure the backend connection:

```swift
class SettingsService: ObservableObject {
    @Published var apiBaseURL: String {
        didSet {
            UserDefaults.standard.set(apiBaseURL, forKey: "api_base_url")
        }
    }
    
    @Published var defaultDeviceType: DeviceType {
        didSet {
            UserDefaults.standard.set(defaultDeviceType.rawValue, forKey: "default_device_type")
        }
    }
    
    init() {
        self.apiBaseURL = UserDefaults.standard.string(forKey: "api_base_url") ?? "http://localhost:8000"
        
        if let savedDeviceType = UserDefaults.standard.string(forKey: "default_device_type"),
           let deviceType = DeviceType(rawValue: savedDeviceType) {
            self.defaultDeviceType = deviceType
        } else {
            self.defaultDeviceType = .macbook
        }
    }
}
```

## ROI Selection and Image Preprocessing

The app performs some image preprocessing before sending to the backend:

```swift
class ImageProcessingService {
    // Crop image to ROI
    static func cropToROI(image: UIImage, roi: CGRect) -> UIImage? {
        let imageSize = image.size
        let scale = image.scale
        
        // Convert ROI from view coordinates to image coordinates
        let scaledROI = CGRect(
            x: roi.origin.x * imageSize.width / viewSize.width,
            y: roi.origin.y * imageSize.height / viewSize.height,
            width: roi.width * imageSize.width / viewSize.width,
            height: roi.height * imageSize.height / viewSize.height
        )
        
        // Crop the image
        guard let cgImage = image.cgImage?.cropping(to: scaledROI) else {
            return nil
        }
        
        return UIImage(cgImage: cgImage, scale: scale, orientation: image.imageOrientation)
    }
    
    // Optimize image for OCR
    static func optimizeForOCR(image: UIImage) -> UIImage {
        // Resize if too large
        let maxDimension: CGFloat = 1200
        var optimizedImage = image
        
        if image.size.width > maxDimension || image.size.height > maxDimension {
            let scale = maxDimension / max(image.size.width, image.size.height)
            let newSize = CGSize(width: image.size.width * scale, height: image.size.height * scale)
            optimizedImage = resize(image: image, to: newSize)
        }
        
        // Convert to JPEG with moderate compression
        if let jpegData = optimizedImage.jpegData(compressionQuality: 0.8),
           let compressedImage = UIImage(data: jpegData) {
            return compressedImage
        }
        
        return optimizedImage
    }
}
```

## Conclusion

This integration guide provides a comprehensive overview of how the iOS frontend communicates with the Apple OCR backend service. By following these patterns, developers can ensure proper interaction between the two components and handle various scenarios including errors and offline operation.

## Additional Resources

- [Backend API Documentation](http://localhost:8000/docs)
- [Combine Framework Documentation](https://developer.apple.com/documentation/combine)
- [URLSession Documentation](https://developer.apple.com/documentation/foundation/urlsession)
