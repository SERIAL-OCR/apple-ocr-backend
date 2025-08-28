import SwiftUI
import Vision
import VisionKit
import AVFoundation
import Combine

@MainActor
class SerialScannerViewModel: ObservableObject {
    // MARK: - Published Properties
    @Published var isProcessing = false
    @Published var guidanceText = "Position the serial number within the frame"
    @Published var showingResultAlert = false
    @Published var resultMessage = ""
    @Published var bestConfidence: Float = 0.0
    @Published var processedFrames = 0
    @Published var isFlashOn = false
    
    // MARK: - Camera Properties
    var previewLayer: AVCaptureVideoPreviewLayer?
    private var captureSession: AVCaptureSession?
    private var videoOutput = AVCaptureVideoDataOutput()
    private var photoOutput = AVCapturePhotoOutput()
    
    // MARK: - Vision Properties
    private var textRecognitionRequest: VNRecognizeTextRequest?
    private var processingQueue = DispatchQueue(label: "com.appleserial.processing", qos: .userInitiated)
    private var roiRectNormalized: CGRect = CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.6) // centered square ROI by default
    
    // MARK: - Configuration
    let maxFrames = 10
    let processingWindow: TimeInterval = 4.0 // 4 seconds window
    let minConfidence: Float = 0.7
    let deviceType = UIDevice.current.model
    
    // MARK: - Frame Processing
    private var frameResults: [FrameResult] = []
    private var processingStartTime: Date?
    private var isAutoCapturing = false
    
    // MARK: - Backend Integration
    private let backendService = BackendService()
    
    // MARK: - Initialization
    init() {
        setupVision()
        setupCamera()
    }
    
    // MARK: - Vision Setup
    private func setupVision() {
        textRecognitionRequest = VNRecognizeTextRequest { [weak self] request, error in
            self?.handleTextRecognition(request: request, error: error)
        }
        
        textRecognitionRequest?.recognitionLevel = .accurate
        textRecognitionRequest?.usesLanguageCorrection = true
        textRecognitionRequest?.recognitionLanguages = ["en-US"]
        textRecognitionRequest?.minimumTextHeight = 0.01
        // Default ROI; can be updated dynamically if UI provides custom ROI
        textRecognitionRequest?.regionOfInterest = roiRectNormalized
    }
    
    // MARK: - Camera Setup
    private func setupCamera() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .high
        
        guard let captureSession = captureSession,
              let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            return
        }
        
        do {
            let input = try AVCaptureDeviceInput(device: camera)
            if captureSession.canAddInput(input) {
                captureSession.addInput(input)
            }
            
            // Setup video output for continuous processing
            videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
            if captureSession.canAddOutput(videoOutput) {
                captureSession.addOutput(videoOutput)
            }
            
            // Setup photo output for manual capture
            if captureSession.canAddOutput(photoOutput) {
                captureSession.addOutput(photoOutput)
            }
            
            // Setup preview layer
            let previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
            previewLayer.videoGravity = .resizeAspectFill
            self.previewLayer = previewLayer
            
        } catch {
            print("Camera setup error: \(error)")
        }
    }
    
    // MARK: - Public Methods
    func startScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.startRunning()
        }
        
        // Start auto-capture after a short delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.startAutoCapture()
        }
    }
    
    func stopScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
        }
        stopAutoCapture()
    }
    
    func manualCapture() {
        guard !isProcessing else { return }
        
        let settings = AVCapturePhotoSettings()
        photoOutput.capturePhoto(with: settings, delegate: self)
    }
    
    func toggleFlash() {
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            return
        }
        
        do {
            try device.lockForConfiguration()
            if device.hasTorch {
                if isFlashOn {
                    device.torchMode = .off
                } else {
                    device.torchMode = .on
                }
                isFlashOn.toggle()
            }
            device.unlockForConfiguration()
        } catch {
            print("Flash toggle error: \(error)")
        }
    }
    
    // MARK: - Auto Capture
    private func startAutoCapture() {
        isAutoCapturing = true
        processingStartTime = Date()
        frameResults.removeAll()
        processedFrames = 0
        bestConfidence = 0.0
        
        updateGuidanceText("Scanning for serial numbers...")
    }
    
    private func stopAutoCapture() {
        isAutoCapturing = false
        processBestResult()
    }
    
    // MARK: - Frame Processing
    private func processFrame(_ image: CGImage) {
        guard isAutoCapturing,
              let processingStartTime = processingStartTime,
              Date().timeIntervalSince(processingStartTime) < processingWindow,
              processedFrames < maxFrames else {
            if isAutoCapturing {
                stopAutoCapture()
            }
            return
        }
        
        processedFrames += 1
        
        guard let textRecognitionRequest = textRecognitionRequest else { return }
        
        // Ensure ROI is applied before each perform in case it changes
        textRecognitionRequest.regionOfInterest = roiRectNormalized
        let handler = VNImageRequestHandler(cgImage: image, orientation: currentCGImageOrientation(), options: [:])
        
        do {
            try handler.perform([textRecognitionRequest])
        } catch {
            print("Vision processing error: \(error)")
        }
    }
    
    // MARK: - Text Recognition Handler
    private func handleTextRecognition(request: VNRequest, error: Error?) {
        guard error == nil else {
            print("Text recognition error: \(error!)")
            return
        }
        
        guard let observations = request.results as? [VNRecognizedTextObservation] else {
            return
        }
        
        for observation in observations {
            guard let topCandidate = observation.topCandidates(1).first else { continue }
            
            let text = topCandidate.string.uppercased()
            let confidence = topCandidate.confidence
            
            // Check if this looks like an Apple serial number
            if isValidAppleSerialFormat(text) {
                let frameResult = FrameResult(
                    text: text,
                    confidence: confidence,
                    timestamp: Date()
                )
                
                frameResults.append(frameResult)
                
                // Update best confidence
                if confidence > bestConfidence {
                    bestConfidence = confidence
                }
                
                // If we have a high confidence result, we can stop early
                if confidence >= 0.85 {
                    DispatchQueue.main.async {
                        self.stopAutoCapture()
                    }
                    return
                }
            }
        }
    }
    
    // MARK: - Result Processing
    private func processBestResult() {
        guard !frameResults.isEmpty else {
            updateGuidanceText("No serial numbers detected. Try again.")
            return
        }
        
        // Sort by confidence and get the best result
        let bestResult = frameResults.max { $0.confidence < $1.confidence }!
        
        // Validate the result
        if bestResult.confidence >= minConfidence {
            submitToBackend(serial: bestResult.text, confidence: bestResult.confidence)
        } else {
            updateGuidanceText("Low confidence result. Please try again.")
        }
    }
    
    // MARK: - Backend Submission
    private func submitToBackend(serial: String, confidence: Float) {
        isProcessing = true
        updateGuidanceText("Submitting to server...")
        
        Task {
            do {
                let result = try await backendService.submitSerial(
                    serial: serial,
                    confidence: confidence,
                    deviceType: deviceType,
                    source: "ios"
                )
                
                await MainActor.run {
                    self.isProcessing = false
                    
                    if result.success {
                        self.resultMessage = "Serial number submitted successfully: \(serial)"
                        self.updateGuidanceText("Success! Ready for next scan.")
                    } else {
                        self.resultMessage = "Submission failed: \(result.message)"
                        self.updateGuidanceText("Submission failed. Please try again.")
                    }
                    
                    self.showingResultAlert = true
                }
                
            } catch {
                await MainActor.run {
                    self.isProcessing = false
                    self.resultMessage = "Network error: \(error.localizedDescription)"
                    self.updateGuidanceText("Network error. Please check connection.")
                    self.showingResultAlert = true
                }
            }
        }
    }
    
    // MARK: - Helper Methods
    private func updateGuidanceText(_ text: String) {
        DispatchQueue.main.async {
            self.guidanceText = text
        }
    }
    
    private func isValidAppleSerialFormat(_ text: String) -> Bool {
        // Apple serial numbers are typically 12 characters, alphanumeric
        let pattern = "^[A-Z0-9]{12}$"
        let regex = try? NSRegularExpression(pattern: pattern)
        let range = NSRange(location: 0, length: text.utf16.count)
        return regex?.firstMatch(in: text, range: range) != nil
    }

    // MARK: - Orientation Helpers
    private func currentCGImageOrientation() -> CGImagePropertyOrientation {
        // Prefer the video connection orientation if available
        if let connection = videoOutput.connection(with: .video) {
            switch connection.videoOrientation {
            case .portrait:
                return .right
            case .portraitUpsideDown:
                return .left
            case .landscapeRight:
                return .down
            case .landscapeLeft:
                return .up
            @unknown default:
                break
            }
        }
        // Fallback to device orientation
        switch UIDevice.current.orientation {
        case .portrait:
            return .right
        case .portraitUpsideDown:
            return .left
        case .landscapeLeft:
            return .up
        case .landscapeRight:
            return .down
        default:
            return .right
        }
    }

    // MARK: - ROI Updates from UI
    func updateRegionOfInterest(from rectInView: CGRect, in viewBounds: CGRect) {
        guard viewBounds.width > 0, viewBounds.height > 0 else { return }
        // Convert from UIKit (origin top-left) to Vision normalized (origin bottom-left)
        let x = rectInView.origin.x / viewBounds.width
        let yTop = rectInView.origin.y / viewBounds.height
        let width = rectInView.width / viewBounds.width
        let height = rectInView.height / viewBounds.height
        // UIKit y from top -> Vision y from bottom: yVision = 1 - yTop - height
        let y = 1.0 - yTop - height
        let normalized = CGRect(x: x, y: y, width: width, height: height)
        roiRectNormalized = normalized
        textRecognitionRequest?.regionOfInterest = normalized
    }
}

// MARK: - Frame Result Model
struct FrameResult {
    let text: String
    let confidence: Float
    let timestamp: Date
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate
extension SerialScannerViewModel: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        let ciImage = CIImage(cvImageBuffer: imageBuffer)
        let context = CIContext()
        
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        
        processFrame(cgImage)
    }
}

// MARK: - AVCapturePhotoCaptureDelegate
extension SerialScannerViewModel: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard error == nil,
              let imageData = photo.fileDataRepresentation(),
              let image = UIImage(data: imageData),
              let cgImage = image.cgImage else {
            return
        }
        
        processFrame(cgImage)
    }
}
