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
    @Published var validationResult: ValidationResult?
    @Published var showValidationAlert = false
    @Published var validationAlertMessage = ""
    
    // MARK: - Camera Properties
    var previewLayer: AVCaptureVideoPreviewLayer?
    private var captureSession: AVCaptureSession?
    private var videoOutput = AVCaptureVideoDataOutput()
    private var photoOutput = AVCapturePhotoOutput()
    
    // MARK: - Vision Properties
    private var textRecognitionRequest: VNRecognizeTextRequest?
    private var processingQueue = DispatchQueue(label: "com.appleserial.processing", qos: .userInitiated)
    private var roiRectNormalized: CGRect = CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.6)
    
    // MARK: - Configuration
    let maxFrames = 10
    let processingWindow: TimeInterval = 4.0
    let minConfidence: Float = 0.7
    let deviceType: String
    
    init() {
        #if os(iOS)
        self.deviceType = UIDevice.current.model
        #else
        self.deviceType = "Mac"
        #endif
        setupVision()
        setupCamera()
    }
    
    // Accessory preset configuration
    private var selectedPreset: String {
        UserDefaults.standard.string(forKey: "selected_preset") ?? "default"
    }
    
    private var isAccessoryPreset: Bool {
        selectedPreset == "accessory"
    }
    
    // MARK: - Frame Processing
    private var frameResults: [FrameResult] = []
    private var processingStartTime: Date?
    private var isAutoCapturing = false
    
    // MARK: - Backend Integration
    private let backendService = BackendService()
    private let validator = AppleSerialValidator()
    
    // MARK: - Vision Setup
    private func setupVision() {
        textRecognitionRequest = VNRecognizeTextRequest { [weak self] request, error in
            self?.handleTextRecognition(request: request, error: error)
        }
        
        textRecognitionRequest?.recognitionLevel = .accurate
        textRecognitionRequest?.usesLanguageCorrection = true
        textRecognitionRequest?.recognitionLanguages = ["en-US"]
        textRecognitionRequest?.minimumTextHeight = getMinimumTextHeight()
        textRecognitionRequest?.regionOfInterest = roiRectNormalized
    }
    
    private func getMinimumTextHeight() -> Float {
        return isAccessoryPreset ? 0.008 : 0.01
    }
    
    // MARK: - Camera Setup
    private func setupCamera() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .high
        
        guard let captureSession = captureSession else { return }
        
        #if os(iOS)
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            return
        }
        #else
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .unspecified) else {
            return
        }
        #endif
        
        do {
            let input = try AVCaptureDeviceInput(device: camera)
            if captureSession.canAddInput(input) {
                captureSession.addInput(input)
            }
            
            videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
            if captureSession.canAddOutput(videoOutput) {
                captureSession.addOutput(videoOutput)
            }
            
            photoOutput = AVCapturePhotoOutput()
            if captureSession.canAddOutput(photoOutput) {
                captureSession.addOutput(photoOutput)
            }
            
            // Setup preview layer
            previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
            previewLayer?.videoGravity = .resizeAspectFill
            
        } catch {
            print("Camera setup error: \(error)")
        }
    }
    
    // MARK: - Camera Control
    func startScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.startRunning()
        }
    }
    
    func stopScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
        }
    }
    
    func manualCapture() {
        guard !isProcessing else { return }
        
        let settings = AVCapturePhotoSettings()
        photoOutput.capturePhoto(with: settings, delegate: self)
    }
    
    func toggleFlash() {
        #if os(iOS)
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
        #else
        isFlashOn = false
        #endif
    }
    
    // MARK: - Auto Capture
    private func startAutoCapture() {
        isAutoCapturing = true
        processingStartTime = Date()
        frameResults.removeAll()
        processedFrames = 0
        bestConfidence = 0.0
        
        updateGuidanceText(getPresetGuidanceText())
    }
    
    private func getPresetGuidanceText() -> String {
        if isAccessoryPreset {
            return "Position accessory serial within frame. Move closer for small text."
        } else {
            return "Position the serial number within the frame"
        }
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
            
            if isValidAppleSerialFormat(text) {
                let frameResult = FrameResult(
                    text: text,
                    confidence: confidence,
                    timestamp: Date()
                )
                frameResults.append(frameResult)
                
                if confidence > bestConfidence {
                    bestConfidence = confidence
                }
                
                // Early stop if we have high confidence
                if confidence >= 0.9 {
                    stopAutoCapture()
                    return
                }
            }
        }
    }
    
    // MARK: - Best Result Processing
    private func processBestResult() {
        guard !frameResults.isEmpty else {
            updateGuidanceText("No serial number detected. Try again.")
            return
        }
        
        let bestResult = frameResults.max { $0.confidence < $1.confidence }!
        
        // Use client-side validation
        let validationResult = validator.validate_with_corrections(bestResult.text, bestResult.confidence)
        
        switch validationResult.level {
        case .ACCEPT:
            submitSerial(validationResult.serial, validationResult.confidence)
        case .BORDERLINE:
            self.validationResult = validationResult
            validationAlertMessage = "Borderline confidence (\(Int(validationResult.confidence * 100))%). Submit anyway?"
            showValidationAlert = true
        case .REJECT:
            updateGuidanceText("Invalid serial detected. Try again.")
        }
    }
    
    // MARK: - Validation Confirmation
    func handleValidationConfirmation(confirmed: Bool) {
        guard let validationResult = validationResult else { return }
        
        if confirmed {
            submitSerial(validationResult.serial, validationResult.confidence)
        }
        
        self.validationResult = nil
        showValidationAlert = false
    }
    
    // MARK: - Backend Submission
    private func submitSerial(_ serial: String, _ confidence: Float) {
        Task {
            do {
                let submission = SerialSubmission(
                    serial: serial,
                    confidence: confidence,
                    device_type: deviceType,
                    source: PlatformDetector.current == .iOS ? "ios" : "mac"
                )
                
                let response = try await backendService.submitSerial(submission)
                
                await MainActor.run {
                    resultMessage = "Serial submitted: \(response.serial)"
                    showingResultAlert = true
                    updateGuidanceText("Serial submitted successfully!")
                }
            } catch {
                await MainActor.run {
                    resultMessage = "Submission failed: \(error.localizedDescription)"
                    showingResultAlert = true
                    updateGuidanceText("Submission failed. Try again.")
                }
            }
        }
    }
    
    // MARK: - Helper Methods
    private func updateGuidanceText(_ text: String) {
        guidanceText = text
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
        
        #if os(iOS)
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
        #else
        return .right
        #endif
    }
    
    // MARK: - ROI Updates from UI
    func updateRegionOfInterest(from rectInView: CGRect, in viewBounds: CGRect) {
        guard viewBounds.width > 0, viewBounds.height > 0 else { return }
        
        var adjustedRect = rectInView
        if isAccessoryPreset {
            let expansion: CGFloat = 20
            adjustedRect = rectInView.insetBy(dx: -expansion, dy: -expansion)
        }
        
        let x = adjustedRect.origin.x / viewBounds.width
        let yTop = adjustedRect.origin.y / viewBounds.height
        let width = adjustedRect.width / viewBounds.width
        let height = adjustedRect.height / viewBounds.height
        let y = 1.0 - yTop - height
        let normalized = CGRect(x: x, y: y, width: width, height: height)
        roiRectNormalized = normalized
        textRecognitionRequest?.regionOfInterest = normalized
        textRecognitionRequest?.minimumTextHeight = getMinimumTextHeight()
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
