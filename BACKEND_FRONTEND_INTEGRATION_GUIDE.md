# Backend-Frontend Integration Guide

## 🎯 Overview

This guide provides the essential information needed to connect the iOS frontend (developed in Xcode) with our enhanced OCR backend API. **We now use an asynchronous architecture to prevent iOS timeout issues.**

## 📡 API Endpoints

### 1. **NEW: Asynchronous Scan Endpoint (Recommended for iOS)**

**Endpoint:** `POST /scan`

**URL:** `http://localhost:8000/scan` (development)

**Request Format:**
```
Content-Type: multipart/form-data

Parameters:
- image: [binary image data]
- device_type: string (e.g., "macbook", "iphone", "ipad")
- preset: string (e.g., "etched", "screen", "sticker") - optional, auto-detected
```

**Response Format (Immediate):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "submitted",
  "message": "Scan received and queued for processing",
  "estimated_time": "10-30 seconds",
  "check_status_url": "/result/550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. **NEW: Check Scan Status Endpoint**

**Endpoint:** `GET /result/{job_id}`

**URL:** `http://localhost:8000/result/{job_id}`

**Response Format:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing", // pending, processing, completed, failed
  "progress": 45,
  "message": "Running OCR analysis...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:15Z",
  "results": null, // Available when status = "completed"
  "error": null
}
```

**Completed Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Successfully detected 3 serial numbers",
  "results": {
    "serials": [
      {"serial": "C02Y942FIG5H", "confidence": 0.85},
      {"serial": "C02Y942FIG5G", "confidence": 0.72}
    ],
    "top_result": {"serial": "C02Y942FIG5H", "confidence": 0.85},
    "total_detected": 2,
    "processing_time": 25.3
  }
}
```

### 3. **Legacy: Synchronous OCR Endpoint (Not recommended for iOS)**

**Endpoint:** `POST /process-serial`

**URL:** `http://localhost:8000/process-serial` (development)

**Note:** This endpoint can take 60+ seconds and may timeout iOS requests.

### 4. Health Check Endpoint

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "ok",
  "gpu": {
    "torch_present": true,
    "cuda_available": false,
    "mps_available": true
  }
}
```

## 🔧 iOS Integration Code (Updated for Async)

### 1. **Updated API Service Class**

```swift
import Foundation
import UIKit
import Combine

class OCRAPIService: ObservableObject {
    static let shared = OCRAPIService()
    
    @Published var isLoading = false
    @Published var lastError: String?
    @Published var currentJob: ScanJob?
    
    private let baseURL = "http://localhost:8000"
    private let session = URLSession.shared
    
    // MARK: - Submit Scan (Async)
    
    func submitScan(
        image: UIImage,
        deviceType: String,
        preset: String? = nil,
        completion: @escaping (Result<ScanSubmission, Error>) -> Void
    ) {
        isLoading = true
        lastError = nil
        
        guard let url = URL(string: "\(baseURL)/scan") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        // Create body
        var body = Data()
        
        // Add image data
        if let imageData = image.jpegData(compressionQuality: 0.8) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
            body.append(imageData)
            body.append("\r\n".data(using: .utf8)!)
        }
        
        // Add device type
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"device_type\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(deviceType)\r\n".data(using: .utf8)!)
        
        // Add preset if provided
        if let preset = preset {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"preset\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(preset)\r\n".data(using: .utf8)!)
        }
        
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body
        
        // Make request
        let task = session.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                self?.isLoading = false
                
                if let error = error {
                    self?.lastError = error.localizedDescription
                    completion(.failure(error))
                    return
                }
                
                guard let data = data else {
                    self?.lastError = "No data received"
                    completion(.failure(APIError.noData))
                    return
                }
                
                do {
                    let submission = try JSONDecoder().decode(ScanSubmission.self, from: data)
                    self?.currentJob = ScanJob(id: submission.job_id, status: .submitted)
                    completion(.success(submission))
                } catch {
                    self?.lastError = "Failed to decode response: \(error.localizedDescription)"
                    completion(.failure(error))
                }
            }
        }
        
        task.resume()
    }
    
    // MARK: - Check Scan Status
    
    func checkScanStatus(jobId: String, completion: @escaping (Result<ScanStatus, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/result/\(jobId)") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        let task = session.dataTask(with: url) { data, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    completion(.failure(error))
                    return
                }
                
                guard let data = data else {
                    completion(.failure(APIError.noData))
                    return
                }
                
                do {
                    let status = try JSONDecoder().decode(ScanStatus.self, from: data)
                    completion(.success(status))
                } catch {
                    completion(.failure(error))
                }
            }
        }
        
        task.resume()
    }
    
    // MARK: - Poll for Results
    
    func pollForResults(jobId: String, completion: @escaping (Result<ScanResults?, Error>) -> Void) {
        checkScanStatus(jobId: jobId) { result in
            switch result {
            case .success(let status):
                if status.status == "completed" {
                    // Parse results
                    if let resultsData = status.results {
                        do {
                            let results = try JSONDecoder().decode(ScanResults.self, from: resultsData)
                            completion(.success(results))
                        } catch {
                            completion(.failure(error))
                        }
                    } else {
                        completion(.success(nil))
                    }
                } else if status.status == "failed" {
                    completion(.failure(APIError.processingFailed(status.error ?? "Unknown error")))
                } else {
                    // Still processing, return nil to indicate polling should continue
                    completion(.success(nil))
                }
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

// MARK: - Response Models

struct ScanSubmission: Codable {
    let job_id: String
    let status: String
    let message: String
    let estimated_time: String
    let check_status_url: String
}

struct ScanStatus: Codable {
    let job_id: String
    let status: String
    let progress: Int
    let message: String
    let created_at: String
    let updated_at: String
    let results: [String: Any]?
    let error: String?
    
    // Custom decoding for results field
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        job_id = try container.decode(String.self, forKey: .job_id)
        status = try container.decode(String.self, forKey: .status)
        progress = try container.decode(Int.self, forKey: .progress)
        message = try container.decode(String.self, forKey: .message)
        created_at = try container.decode(String.self, forKey: .created_at)
        updated_at = try container.decode(String.self, forKey: .updated_at)
        error = try container.decodeIfPresent(String.self, forKey: .error)
        
        // Handle results as Any
        if let resultsData = try container.decodeIfPresent(Data.self, forKey: .results) {
            results = try JSONSerialization.jsonObject(with: resultsData) as? [String: Any]
        } else {
            results = nil
        }
    }
    
    private enum CodingKeys: String, CodingKey {
        case job_id, status, progress, message, created_at, updated_at, results, error
    }
}

struct ScanResults: Codable {
    let serials: [SerialResult]
    let top_result: SerialResult
    let total_detected: Int
    let processing_time: Double
}

struct SerialResult: Codable {
    let serial: String
    let confidence: Double
}

struct ScanJob {
    let id: String
    var status: ScanJobStatus
    
    enum ScanJobStatus {
        case submitted
        case processing
        case completed
        case failed
    }
}

enum APIError: Error {
    case invalidURL
    case noData
    case networkError(String)
    case processingFailed(String)
}
```

### 2. **Updated SwiftUI View with Async Processing**

```swift
struct ScannerView: View {
    @StateObject private var apiService = OCRAPIService.shared
    @State private var selectedDeviceType: DeviceType = .macbook
    @State private var capturedImage: UIImage?
    @State private var scanResult: SerialResult?
    @State private var showingImagePicker = false
    @State private var isPolling = false
    @State private var pollingTimer: Timer?
    
    var body: some View {
        VStack {
            // Device type selector
            Picker("Device Type", selection: $selectedDeviceType) {
                ForEach(DeviceType.allCases, id: \.self) { deviceType in
                    Text(deviceType.displayName).tag(deviceType)
                }
            }
            .pickerStyle(SegmentedPickerStyle())
            .padding()
            
            // Image display
            if let image = capturedImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(height: 300)
                    .padding()
            }
            
            // Capture buttons
            HStack {
                Button("Take Photo") {
                    // Implement camera capture
                }
                
                Button("Choose Photo") {
                    showingImagePicker = true
                }
            }
            .padding()
            
            // Process button
            if capturedImage != nil && !isPolling {
                Button("Process Image") {
                    submitScan()
                }
                .disabled(apiService.isLoading)
                .padding()
            }
            
            // Loading indicator
            if apiService.isLoading {
                ProgressView("Submitting scan...")
                    .padding()
            }
            
            // Polling status
            if isPolling, let job = apiService.currentJob {
                VStack {
                    ProgressView("Processing scan...")
                        .padding()
                    Text("Job ID: \(job.id)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            // Error display
            if let error = apiService.lastError {
                Text("Error: \(error)")
                    .foregroundColor(.red)
                    .padding()
            }
            
            // Result display
            if let result = scanResult {
                VStack {
                    Text("Serial: \(result.serial)")
                        .font(.headline)
                    Text("Confidence: \(Int(result.confidence * 100))%")
                        .font(.subheadline)
                }
                .padding()
            }
        }
        .sheet(isPresented: $showingImagePicker) {
            ImagePicker(selectedImage: $capturedImage)
        }
        .onDisappear {
            stopPolling()
        }
    }
    
    private func submitScan() {
        guard let image = capturedImage else { return }
        
        apiService.submitScan(
            image: image,
            deviceType: selectedDeviceType.rawValue,
            preset: selectedDeviceType.preset
        ) { result in
            switch result {
            case .success(let submission):
                print("Scan submitted: \(submission.job_id)")
                startPolling(jobId: submission.job_id)
            case .failure(let error):
                print("Submission failed: \(error)")
            }
        }
    }
    
    private func startPolling(jobId: String) {
        isPolling = true
        
        // Poll every 2 seconds
        pollingTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { _ in
            apiService.pollForResults(jobId: jobId) { result in
                switch result {
                case .success(let results):
                    if let results = results {
                        // Processing completed
                        scanResult = results.top_result
                        stopPolling()
                    }
                    // Continue polling if nil (still processing)
                case .failure(let error):
                    print("Polling failed: \(error)")
                    stopPolling()
                }
            }
        }
    }
    
    private func stopPolling() {
        isPolling = false
        pollingTimer?.invalidate()
        pollingTimer = nil
    }
}
```

## 🔧 Backend Setup for Testing

### 1. Start the Backend Server

```bash
# Navigate to backend directory
cd /Users/Apple/Documents/apple-ocr-backend

# Activate virtual environment
source .venv/bin/activate

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test New Async Endpoints

```bash
# Submit a scan (returns immediately)
curl -X POST http://localhost:8000/scan \
  -F "image=@samples/synthetic_01_clean_5OYFMUL3L2OE.png" \
  -F "device_type=macbook"

# Check status (poll this endpoint)
curl http://localhost:8000/result/{job_id}

# List all jobs
curl http://localhost:8000/jobs
```

## 📱 iOS App Configuration

### 1. Network Security

Add to `Info.plist`:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

### 2. Camera Permissions

Add to `Info.plist`:
```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to capture serial numbers.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>This app needs photo library access to select images.</string>
```

## 🧪 Testing Checklist

- [ ] Backend server running on localhost:8000
- [ ] `/scan` endpoint returns job ID immediately
- [ ] `/result/{job_id}` shows processing progress
- [ ] iOS app can submit scans without timeout
- [ ] iOS app can poll for results
- [ ] Results display correctly when processing completes
- [ ] Error handling works for failed jobs

## 🚀 Benefits of New Async Architecture

1. **No More Timeouts**: iOS app gets immediate response
2. **Better UX**: Users see progress updates
3. **Scalable**: Backend can process multiple jobs
4. **Robust**: Failed jobs don't block the app
5. **Real-time Updates**: Progress tracking and status updates

## 🔍 Troubleshooting

### Common Issues:

1. **Connection refused**: Make sure backend server is running
2. **Job not found**: Check if job has expired (1 hour limit)
3. **Polling not working**: Ensure timer is properly managed
4. **Results not showing**: Check job status before parsing results

### Debug Mode:

- Use `/jobs` endpoint to see all active jobs
- Check job status with `/result/{job_id}`
- Monitor backend logs for processing details
