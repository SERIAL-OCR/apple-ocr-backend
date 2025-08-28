import SwiftUI
import Vision
import VisionKit
import AVFoundation
import Combine

struct SerialScannerView: View {
    @StateObject private var scannerViewModel = SerialScannerViewModel()
    @State private var showingSettings = false
    @State private var showingHistory = false
    
    var body: some View {
        NavigationView {
            ZStack {
                // Camera preview with overlay
                CameraPreviewView(scannerViewModel: scannerViewModel)
                    .ignoresSafeArea()
                
                // ROI overlay and guidance
                ScannerOverlayView(scannerViewModel: scannerViewModel)
                
                // Status and feedback UI
                VStack {
                    Spacer()
                    
                    // Status bar
                    StatusBarView(scannerViewModel: scannerViewModel)
                    
                    // Control buttons
                    ControlButtonsView(scannerViewModel: scannerViewModel)
                }
                .padding()
            }
            .navigationTitle("Apple Serial Scanner")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Settings") {
                        showingSettings = true
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("History") {
                        showingHistory = true
                    }
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
        }
        .sheet(isPresented: $showingHistory) {
            HistoryView()
        }
        .alert("Scan Result", isPresented: $scannerViewModel.showingResultAlert) {
            Button("OK") { }
        } message: {
            Text(scannerViewModel.resultMessage)
        }
        .onAppear {
            scannerViewModel.startScanning()
        }
        .onDisappear {
            scannerViewModel.stopScanning()
        }
    }
}

// MARK: - Camera Preview View
struct CameraPreviewView: UIViewRepresentable {
    @ObservedObject var scannerViewModel: SerialScannerViewModel
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        view.backgroundColor = .black
        
        // Add camera preview layer
        if let previewLayer = scannerViewModel.previewLayer {
            previewLayer.frame = view.bounds
            previewLayer.videoGravity = .resizeAspectFill
            view.layer.addSublayer(previewLayer)
        }
        
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = scannerViewModel.previewLayer {
            previewLayer.frame = uiView.bounds
        }
    }
}

// MARK: - Scanner Overlay View
struct ScannerOverlayView: View {
    @ObservedObject var scannerViewModel: SerialScannerViewModel
    @State private var roiRect: CGRect = .zero
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Semi-transparent overlay
                Rectangle()
                    .fill(Color.black.opacity(0.3))
                    .ignoresSafeArea()
                
                // Auto square ROI (centered)
                let side = min(geometry.size.width, geometry.size.height) * 0.6
                let roi = CGRect(
                    x: (geometry.size.width - side) / 2.0,
                    y: (geometry.size.height - side) / 2.0,
                    width: side,
                    height: side
                )
                Color.clear
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
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white, lineWidth: 3)
                    .frame(width: roi.width, height: roi.height)
                    .position(x: roi.midX, y: roi.midY)
                
                // Corner indicators
                CornerIndicator(position: .topLeft)
                    .position(x: roi.minX + 20, y: roi.minY + 20)
                CornerIndicator(position: .topRight)
                    .position(x: roi.maxX - 20, y: roi.minY + 20)
                CornerIndicator(position: .bottomLeft)
                    .position(x: roi.minX + 20, y: roi.maxY - 20)
                CornerIndicator(position: .bottomRight)
                    .position(x: roi.maxX - 20, y: roi.maxY - 20)
                
                // Guidance text
                VStack {
                    Spacer()
                    
                    Text(scannerViewModel.guidanceText)
                        .foregroundColor(.white)
                        .font(.headline)
                        .multilineTextAlignment(.center)
                        .padding()
                        .background(Color.black.opacity(0.7))
                        .cornerRadius(8)
                        .padding(.bottom, 100)
                }
                
                // Confidence indicator
                if scannerViewModel.isProcessing {
                    VStack {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(1.5)
                        
                        Text("Processing...")
                            .foregroundColor(.white)
                            .font(.caption)
                    }
                    .padding()
                    .background(Color.black.opacity(0.7))
                    .cornerRadius(8)
                }
            }
        }
    }
}

// MARK: - Corner Indicator
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

// MARK: - Status Bar View
struct StatusBarView: View {
    @ObservedObject var scannerViewModel: SerialScannerViewModel
    
    var body: some View {
        HStack {
            // Device type indicator
            HStack {
                Image(systemName: "iphone")
                Text(scannerViewModel.deviceType)
            }
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.blue.opacity(0.8))
            .cornerRadius(20)
            
            Spacer()
            
            // Confidence indicator
            if scannerViewModel.bestConfidence > 0 {
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                    Text("\(Int(scannerViewModel.bestConfidence * 100))%")
                }
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.green.opacity(0.8))
                .cornerRadius(20)
            }
            
            Spacer()
            
            // Frame counter
            HStack {
                Image(systemName: "camera.fill")
                Text("\(scannerViewModel.processedFrames)/\(scannerViewModel.maxFrames)")
            }
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.orange.opacity(0.8))
            .cornerRadius(20)
        }
        .padding(.horizontal)
    }
}

// MARK: - Control Buttons View
struct ControlButtonsView: View {
    @ObservedObject var scannerViewModel: SerialScannerViewModel
    
    var body: some View {
        HStack(spacing: 30) {
            // Manual capture button
            Button(action: {
                scannerViewModel.manualCapture()
            }) {
                Image(systemName: "camera.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.white)
            }
            .disabled(scannerViewModel.isProcessing)
            
            // Flash toggle
            Button(action: {
                scannerViewModel.toggleFlash()
            }) {
                Image(systemName: scannerViewModel.isFlashOn ? "bolt.fill" : "bolt.slash.fill")
                    .font(.system(size: 30))
                    .foregroundColor(.white)
                    .padding()
                    .background(Color.black.opacity(0.5))
                    .clipShape(Circle())
            }
        }
        .padding(.bottom, 50)
    }
}

// MARK: - Preview
struct SerialScannerView_Previews: PreviewProvider {
    static var previews: some View {
        SerialScannerView()
    }
}
