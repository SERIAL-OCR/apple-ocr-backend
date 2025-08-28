import SwiftUI

// MARK: - Settings View
struct SettingsView: View {
    @StateObject private var settingsViewModel = SettingsViewModel()
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            Form {
                Section("Backend Configuration") {
                    HStack {
                        Text("Server URL")
                        Spacer()
                        TextField("http://localhost:8000", text: $settingsViewModel.serverURL)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .frame(width: 200)
                    }
                    
                    HStack {
                        Text("API Key")
                        Spacer()
                        SecureField("API Key", text: $settingsViewModel.apiKey)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .frame(width: 200)
                    }
                    
                    Button("Test Connection") {
                        Task {
                            await settingsViewModel.testConnection()
                        }
                    }
                    .disabled(settingsViewModel.isTesting)
                    
                    if settingsViewModel.isTesting {
                        HStack {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Testing connection...")
                        }
                    }
                    
                    if let connectionStatus = settingsViewModel.connectionStatus {
                        HStack {
                            Image(systemName: connectionStatus ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundColor(connectionStatus ? .green : .red)
                            Text(connectionStatus ? "Connected" : "Connection failed")
                        }
                    }
                }
                
                Section("Scanner Configuration") {
                    HStack {
                        Text("Max Frames")
                        Spacer()
                        Stepper("\(settingsViewModel.maxFrames)", value: $settingsViewModel.maxFrames, in: 5...20)
                    }
                    
                    HStack {
                        Text("Processing Window")
                        Spacer()
                        Stepper("\(Int(settingsViewModel.processingWindow))s", value: $settingsViewModel.processingWindow, in: 2...10)
                    }
                    
                    HStack {
                        Text("Min Confidence")
                        Spacer()
                        Text("\(Int(settingsViewModel.minConfidence * 100))%")
                        Slider(value: $settingsViewModel.minConfidence, in: 0.3...0.9, step: 0.05)
                    }
                }
                
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Phase")
                        Spacer()
                        Text("2.2")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        settingsViewModel.saveSettings()
                        dismiss()
                    }
                }
            }
        }
        .onAppear {
            settingsViewModel.loadSettings()
        }
    }
}

// MARK: - Settings ViewModel
class SettingsViewModel: ObservableObject {
    @Published var serverURL = "http://localhost:8000"
    @Published var apiKey = "phase2-pilot-key-2024"
    @Published var maxFrames = 10
    @Published var processingWindow: Double = 4.0
    @Published var minConfidence: Double = 0.65
    @Published var isTesting = false
    @Published var connectionStatus: Bool?
    
    private let backendService = BackendService()
    
    func loadSettings() {
        serverURL = UserDefaults.standard.string(forKey: "backend_base_url") ?? "http://localhost:8000"
        apiKey = UserDefaults.standard.string(forKey: "api_key") ?? "phase2-pilot-key-2024"
        maxFrames = UserDefaults.standard.integer(forKey: "max_frames")
        if maxFrames == 0 { maxFrames = 10 }
        processingWindow = UserDefaults.standard.double(forKey: "processing_window")
        if processingWindow == 0 { processingWindow = 4.0 }
        minConfidence = UserDefaults.standard.double(forKey: "min_confidence")
        if minConfidence == 0 { minConfidence = 0.65 }
    }
    
    func saveSettings() {
        UserDefaults.standard.set(serverURL, forKey: "backend_base_url")
        UserDefaults.standard.set(apiKey, forKey: "api_key")
        UserDefaults.standard.set(maxFrames, forKey: "max_frames")
        UserDefaults.standard.set(processingWindow, forKey: "processing_window")
        UserDefaults.standard.set(minConfidence, forKey: "min_confidence")
    }
    
    @MainActor
    func testConnection() async {
        isTesting = true
        connectionStatus = nil
        
        do {
            let isHealthy = try await backendService.healthCheck()
            connectionStatus = isHealthy
        } catch {
            connectionStatus = false
        }
        
        isTesting = false
    }
}

// MARK: - History View
struct HistoryView: View {
    @StateObject private var historyViewModel = HistoryViewModel()
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            Group {
                if historyViewModel.isLoading {
                    VStack {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("Loading history...")
                            .padding()
                    }
                } else if let error = historyViewModel.error {
                    VStack {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        Text("Error loading history")
                            .font(.headline)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        Button("Retry") {
                            Task {
                                await historyViewModel.loadHistory()
                            }
                        }
                        .buttonStyle(.borderedProminent)
                    }
                } else {
                    List {
                        Section {
                            ForEach(historyViewModel.scanHistory?.recentScans ?? [], id: \.id) { scan in
                                ScanHistoryRow(scan: scan)
                            }
                        } header: {
                            if let stats = historyViewModel.scanHistory?.statistics {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Total Scans: \(stats.totalSerials)")
                                        .font(.headline)
                                    HStack {
                                        Text("iOS: \(stats.bySource.ios)")
                                        Text("Mac: \(stats.bySource.mac)")
                                        Text("Server: \(stats.bySource.server)")
                                    }
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Scan History")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Export") {
                        Task {
                            await historyViewModel.exportData()
                        }
                    }
                    .disabled(historyViewModel.isExporting)
                }
            }
            .refreshable {
                await historyViewModel.loadHistory()
            }
        }
        .onAppear {
            Task {
                await historyViewModel.loadHistory()
            }
        }
    }
}

// MARK: - Scan History Row
struct ScanHistoryRow: View {
    let scan: ScanRecord
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(scan.serial)
                    .font(.headline)
                    .fontWeight(.semibold)
                
                Spacer()
                
                Text("\(Int(scan.confidence * 100))%")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(confidenceColor.opacity(0.2))
                    .foregroundColor(confidenceColor)
                    .cornerRadius(4)
            }
            
            HStack {
                Label(scan.deviceType, systemImage: deviceIcon)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(scan.timestamp)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            HStack {
                Label(scan.source.uppercased(), systemImage: "iphone")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(scan.status)
                    .font(.caption)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(statusColor.opacity(0.2))
                    .foregroundColor(statusColor)
                    .cornerRadius(4)
            }
        }
        .padding(.vertical, 4)
    }
    
    private var deviceIcon: String {
        switch scan.deviceType.lowercased() {
        case let device where device.contains("iphone"):
            return "iphone"
        case let device where device.contains("ipad"):
            return "ipad"
        case let device where device.contains("mac"):
            return "laptopcomputer"
        default:
            return "desktopcomputer"
        }
    }
    
    private var confidenceColor: Color {
        if scan.confidence >= 0.8 {
            return .green
        } else if scan.confidence >= 0.6 {
            return .orange
        } else {
            return .red
        }
    }
    
    private var statusColor: Color {
        scan.status == "completed" ? .green : .red
    }
}

// MARK: - History ViewModel
@MainActor
class HistoryViewModel: ObservableObject {
    @Published var scanHistory: ScanHistory?
    @Published var isLoading = false
    @Published var error: String?
    @Published var isExporting = false
    
    private let backendService = BackendService()
    
    func loadHistory() async {
        isLoading = true
        error = nil
        
        do {
            scanHistory = try await backendService.fetchHistory(limit: 100)
        } catch {
            self.error = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func exportData() async {
        isExporting = true
        
        do {
            let data = try await backendService.downloadExport()
            
            // Save to documents directory
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let fileName = "apple_serials_\(Date().timeIntervalSince1970).xlsx"
            let fileURL = documentsPath.appendingPathComponent(fileName)
            
            try data.write(to: fileURL)
            
            // Share the file
            let activityVC = UIActivityViewController(activityItems: [fileURL], applicationActivities: nil)
            
            if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
               let window = windowScene.windows.first {
                window.rootViewController?.present(activityVC, animated: true)
            }
            
        } catch {
            self.error = "Export failed: \(error.localizedDescription)"
        }
        
        isExporting = false
    }
}
