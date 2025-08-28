import SwiftUI
import Vision
import AVFoundation
import AppKit

struct SerialScannerView: View {
    @StateObject private var scannerViewModel = MacSerialScannerViewModel()
    @State private var showingSettings = false
    @State private var showingHistory = false
    @State private var roiRect: CGRect = .zero
    
    var body: some View {
        NavigationView {
            VStack {
                // Camera preview
                CameraPreviewView(scannerViewModel: scannerViewModel)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .overlay(
                        GeometryReader { geometry in
                            let side = min(geometry.size.width, geometry.size.height) * 0.6
                            let roi = CGRect(
                                x: (geometry.size.width - side) / 2.0,
                                y: (geometry.size.height - side) / 2.0,
                                width: side,
                                height: side
                            )
                            ZStack {
                                RoundedRectangle(cornerRadius: 12)
                                    .stroke(Color.white, lineWidth: 3)
                                    .frame(width: roi.width, height: roi.height)
                                    .position(x: roi.midX, y: roi.midY)
                                CornerIndicator(position: .topLeft)
                                    .position(x: roi.minX + 20, y: roi.minY + 20)
                                CornerIndicator(position: .topRight)
                                    .position(x: roi.maxX - 20, y: roi.minY + 20)
                                CornerIndicator(position: .bottomLeft)
                                    .position(x: roi.minX + 20, y: roi.maxY - 20)
                                CornerIndicator(position: .bottomRight)
                                    .position(x: roi.maxX - 20, y: roi.maxY - 20)
                            }
                            .onAppear {
                                roiRect = roi
                                scannerViewModel.updateRegionOfInterest(from: roi, in: CGRect(origin: .zero, size: geometry.size))
                            }
                            .onChange(of: geometry.size) { _ in
                                let updatedSide = min(geometry.size.width, geometry.size.height) * 0.6
                                let updated = CGRect(
                                    x: (geometry.size.width - updatedSide) / 2.0,
                                    y: (geometry.size.height - updatedSide) / 2.0,
                                    width: updatedSide,
                                    height: updatedSide
                                )
                                roiRect = updated
                                scannerViewModel.updateRegionOfInterest(from: updated, in: CGRect(origin: .zero, size: geometry.size))
                            }
                        }
                    )
                
                // Controls
                HStack {
                    Button("Start Scanning") {
                        scannerViewModel.startScanning()
                    }
                    .disabled(scannerViewModel.isScanning)
                    
                    Button("Stop Scanning") {
                        scannerViewModel.stopScanning()
                    }
                    .disabled(!scannerViewModel.isScanning)
                    
                    Button("Settings") {
                        showingSettings = true
                    }
                    
                    Button("History") {
                        showingHistory = true
                    }
                    
                    Spacer()
                    
                    if scannerViewModel.isProcessing {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("Processing...")
                    }
                }
                .padding()
            }
            .navigationTitle("Apple Serial Scanner - macOS")
            .frame(minWidth: 800, minHeight: 600)
        }
        .sheet(isPresented: $showingSettings) {
            MacSettingsView()
        }
        .sheet(isPresented: $showingHistory) {
            MacHistoryView()
        }
        .alert("Scan Result", isPresented: $scannerViewModel.showingResultAlert) {
            Button("OK") { }
        } message: {
            Text(scannerViewModel.resultMessage)
        }
    }
}

// MARK: - Camera Preview View
struct CameraPreviewView: NSViewRepresentable {
    @ObservedObject var scannerViewModel: MacSerialScannerViewModel
    
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor.black.cgColor
        
        if let previewLayer = scannerViewModel.previewLayer {
            previewLayer.frame = view.bounds
            previewLayer.videoGravity = .resizeAspectFill
            view.layer?.addSublayer(previewLayer)
        }
        
        return view
    }
    
    func updateNSView(_ nsView: NSView, context: Context) {
        if let previewLayer = scannerViewModel.previewLayer {
            previewLayer.frame = nsView.bounds
        }
    }
}

// MARK: - macOS Scanner ViewModel
@MainActor
class MacSerialScannerViewModel: ObservableObject {
    @Published var isScanning = false
    @Published var isProcessing = false
    @Published var showingResultAlert = false
    @Published var resultMessage = ""
    @Published var bestConfidence: Float = 0.0
    @Published var processedFrames = 0
    
    // Camera properties
    var previewLayer: AVCaptureVideoPreviewLayer?
    private var captureSession: AVCaptureSession?
    private var videoOutput = AVCaptureVideoDataOutput()
    
    // Vision properties
    private var textRecognitionRequest: VNRecognizeTextRequest?
    private var processingQueue = DispatchQueue(label: "com.appleserial.mac.processing", qos: .userInitiated)
    private var roiRectNormalized: CGRect = CGRect(x: 0.1, y: 0.4, width: 0.8, height: 0.2)
    
    // Configuration
    let maxFrames = 10
    let processingWindow: TimeInterval = 4.0
    let minConfidence: Float = 0.65
    let deviceType = "Mac"
    
    // Frame processing
    private var frameResults: [FrameResult] = []
    private var processingStartTime: Date?
    
    // Backend integration
    private let backendService = BackendService()
    
    init() {
        setupVision()
        setupCamera()
    }
    
    private func setupVision() {
        textRecognitionRequest = VNRecognizeTextRequest { [weak self] request, error in
            self?.handleTextRecognition(request: request, error: error)
        }
        
        textRecognitionRequest?.recognitionLevel = .accurate
        textRecognitionRequest?.usesLanguageCorrection = true
        textRecognitionRequest?.recognitionLanguages = ["en-US"]
        textRecognitionRequest?.minimumTextHeight = 0.01
        textRecognitionRequest?.regionOfInterest = roiRectNormalized
    }
    
    private func setupCamera() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .high
        
        guard let captureSession = captureSession,
              let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .unspecified) else {
            return
        }
        
        do {
            let input = try AVCaptureDeviceInput(device: camera)
            if captureSession.canAddInput(input) {
                captureSession.addInput(input)
            }
            
            videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
            if captureSession.canAddOutput(videoOutput) {
                captureSession.addOutput(videoOutput)
            }
            
            let previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
            previewLayer.videoGravity = .resizeAspectFill
            self.previewLayer = previewLayer
            
        } catch {
            print("Camera setup error: \(error)")
        }
    }
    
    func startScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.startRunning()
        }
        
        isScanning = true
        startAutoCapture()
    }
    
    func stopScanning() {
        processingQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
        }
        
        isScanning = false
        stopAutoCapture()
    }
    
    private func startAutoCapture() {
        processingStartTime = Date()
        frameResults.removeAll()
        processedFrames = 0
        bestConfidence = 0.0
    }
    
    private func stopAutoCapture() {
        processBestResult()
    }
    
    private func processFrame(_ image: CGImage) {
        guard isScanning,
              let processingStartTime = processingStartTime,
              Date().timeIntervalSince(processingStartTime) < processingWindow,
              processedFrames < maxFrames else {
            if isScanning {
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
                
                if confidence >= 0.85 {
                    DispatchQueue.main.async {
                        self.stopAutoCapture()
                    }
                    return
                }
            }
        }
    }
    
    private func processBestResult() {
        guard !frameResults.isEmpty else {
            resultMessage = "No serial numbers detected. Try again."
            showingResultAlert = true
            return
        }
        
        let bestResult = frameResults.max { $0.confidence < $1.confidence }!
        
        if bestResult.confidence >= minConfidence {
            submitToBackend(serial: bestResult.text, confidence: bestResult.confidence)
        } else {
            resultMessage = "Low confidence result. Please try again."
            showingResultAlert = true
        }
    }
    
    private func submitToBackend(serial: String, confidence: Float) {
        isProcessing = true
        
        Task {
            do {
                let result = try await backendService.submitSerial(
                    serial: serial,
                    confidence: confidence,
                    deviceType: deviceType,
                    source: "mac"
                )
                
                await MainActor.run {
                    self.isProcessing = false
                    
                    if result.success {
                        self.resultMessage = "Serial number submitted successfully: \(serial)"
                    } else {
                        self.resultMessage = "Submission failed: \(result.message)"
                    }
                    
                    self.showingResultAlert = true
                }
                
            } catch {
                await MainActor.run {
                    self.isProcessing = false
                    self.resultMessage = "Network error: \(error.localizedDescription)"
                    self.showingResultAlert = true
                }
            }
        }
    }
    
    private func isValidAppleSerialFormat(_ text: String) -> Bool {
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
        return .up
    }
}

// MARK: - ROI Updates from UI (macOS)
extension MacSerialScannerViewModel {
    func updateRegionOfInterest(from rectInView: CGRect, in viewBounds: CGRect) {
        guard viewBounds.width > 0, viewBounds.height > 0 else { return }
        // AppKit coordinates origin at bottom-left for layer-backed views, but GeometryReader uses top-left.
        let x = rectInView.origin.x / viewBounds.width
        let yTop = rectInView.origin.y / viewBounds.height
        let width = rectInView.width / viewBounds.width
        let height = rectInView.height / viewBounds.height
        let y = 1.0 - yTop - height
        let normalized = CGRect(x: x, y: y, width: width, height: height)
        roiRectNormalized = normalized
        textRecognitionRequest?.regionOfInterest = normalized
    }
}

// MARK: - Corner Indicator (macOS)
struct CornerIndicator: View {
    enum Position {
        case topLeft, topRight, bottomLeft, bottomRight
    }
    let position: Position
    var body: some View {
        Path { path in
            let size: CGFloat = 30
            let thickness: CGFloat = 4
            switch position {
            case .topLeft:
                path.move(to: CGPoint(x: thickness, y: 0))
                path.addLine(to: CGPoint(x: size, y: 0))
                path.move(to: CGPoint(x: 0, y: thickness))
                path.addLine(to: CGPoint(x: 0, y: size))
            case .topRight:
                path.move(to: CGPoint(x: 0, y: 0))
                path.addLine(to: CGPoint(x: size - thickness, y: 0))
                path.move(to: CGPoint(x: size, y: thickness))
                path.addLine(to: CGPoint(x: size, y: size))
            case .bottomLeft:
                path.move(to: CGPoint(x: thickness, y: size))
                path.addLine(to: CGPoint(x: size, y: size))
                path.move(to: CGPoint(x: 0, y: 0))
                path.addLine(to: CGPoint(x: 0, y: size - thickness))
            case .bottomRight:
                path.move(to: CGPoint(x: 0, y: size))
                path.addLine(to: CGPoint(x: size - thickness, y: size))
                path.move(to: CGPoint(x: size, y: 0))
                path.addLine(to: CGPoint(x: size, y: size - thickness))
            }
        }
        .stroke(Color.white, lineWidth: 4)
        .frame(width: 30, height: 30)
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate
extension MacSerialScannerViewModel: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        let ciImage = CIImage(cvImageBuffer: imageBuffer)
        let context = CIContext()
        
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        
        processFrame(cgImage)
    }
}

// MARK: - Supporting Views
struct MacSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack {
            Text("macOS Settings")
                .font(.title)
            Text("Settings functionality to be implemented")
                .foregroundColor(.secondary)
            Button("Done") {
                dismiss()
            }
        }
        .padding()
        .frame(width: 400, height: 300)
    }
}

struct MacHistoryView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack {
            Text("macOS History")
                .font(.title)
            Text("History functionality to be implemented")
                .foregroundColor(.secondary)
            Button("Done") {
                dismiss()
            }
        }
        .padding()
        .frame(width: 600, height: 400)
    }
}

// MARK: - Preview
struct SerialScannerView_Previews: PreviewProvider {
    static var previews: some View {
        SerialScannerView()
    }
}
