import Foundation

// MARK: - Models
struct SerialSubmission: Codable {
    let serial: String
    let confidence: Float
    let deviceType: String?
    let source: String
    let ts: Date?
    let notes: String?
    
    enum CodingKeys: String, CodingKey {
        case serial, confidence, source, ts, notes
        case deviceType = "device_type"
    }
}

struct SerialResponse: Codable {
    let success: Bool
    let serialId: String?
    let message: String
    let validationPassed: Bool
    let confidenceAcceptable: Bool
    let timestamp: Date
    
    enum CodingKeys: String, CodingKey {
        case success, message, timestamp
        case serialId = "serial_id"
        case validationPassed = "validation_passed"
        case confidenceAcceptable = "confidence_acceptable"
    }
}

struct ScanHistory: Codable {
    let totalScans: Int
    let recentScans: [ScanRecord]
    let statistics: ScanStatistics
    let exportUrl: String
    
    enum CodingKeys: String, CodingKey {
        case totalScans = "total_scans"
        case recentScans = "recent_scans"
        case statistics, exportUrl = "export_url"
    }
}

struct ScanRecord: Codable {
    let id: Int
    let timestamp: String
    let serial: String
    let deviceType: String
    let confidence: Float
    let source: String
    let notes: String?
    let validationPassed: Bool
    let confidenceAcceptable: Bool
    let status: String
    
    enum CodingKeys: String, CodingKey {
        case id, timestamp, serial, confidence, source, notes, status
        case deviceType = "device_type"
        case validationPassed = "validation_passed"
        case confidenceAcceptable = "confidence_acceptable"
    }
}

struct ScanStatistics: Codable {
    let totalSerials: Int
    let bySource: SourceStats
    let validationStats: ValidationStats
    let avgConfidence: Float
    
    enum CodingKeys: String, CodingKey {
        case totalSerials = "total_serials"
        case bySource = "by_source"
        case validationStats = "validation_stats"
        case avgConfidence = "avg_confidence"
    }
}

struct SourceStats: Codable {
    let ios: Int
    let mac: Int
    let server: Int
}

struct ValidationStats: Codable {
    let valid: Int
    let confidenceAcceptable: Int
    
    enum CodingKeys: String, CodingKey {
        case valid
        case confidenceAcceptable = "confidence_acceptable"
    }
}

struct SystemStats: Codable {
    let database: ScanStatistics
    let system: SystemHealth
    let phase: String
    let timestamp: String
}

struct SystemHealth: Codable {
    let uptime: String
    let lastActivity: String
    
    enum CodingKeys: String, CodingKey {
        case uptime
        case lastActivity = "last_activity"
    }
}

struct ClientConfig: Codable {
    let minAcceptanceConfidence: Float
    let minSubmissionConfidence: Float
    let productionMode: Bool
    let rateLimitingEnabled: Bool
    let maxSubmissionsPerMinute: Int
    
    enum CodingKeys: String, CodingKey {
        case minAcceptanceConfidence = "min_acceptance_confidence"
        case minSubmissionConfidence = "min_submission_confidence"
        case productionMode = "production_mode"
        case rateLimitingEnabled = "rate_limiting_enabled"
        case maxSubmissionsPerMinute = "max_submissions_per_minute"
    }
}

// MARK: - Backend Service
class BackendService {
    private let baseURL: String
    private let apiKey: String
    private let session: URLSession
    
    init() {
        // Load configuration from UserDefaults or use defaults
        self.baseURL = UserDefaults.standard.string(forKey: "backend_base_url") ?? "http://localhost:8000"
        self.apiKey = UserDefaults.standard.string(forKey: "api_key") ?? "phase2-pilot-key-2024"
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30.0
        config.timeoutIntervalForResource = 60.0
        self.session = URLSession(configuration: config)
    }
    
    // MARK: - Serial Submission
    func submitSerial(
        serial: String,
        confidence: Float,
        deviceType: String,
        source: String,
        notes: String? = nil
    ) async throws -> SerialResponse {
        let submission = SerialSubmission(
            serial: serial,
            confidence: confidence,
            deviceType: deviceType,
            source: source,
            ts: Date(),
            notes: notes
        )
        
        let url = URL(string: "\(baseURL)/serials")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        request.httpBody = try encoder.encode(submission)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BackendError.httpError(statusCode: httpResponse.statusCode)
        }
        
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(SerialResponse.self, from: data)
    }
    
    // MARK: - History
    func fetchHistory(limit: Int = 50) async throws -> ScanHistory {
        let url = URL(string: "\(baseURL)/history?limit=\(limit)")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BackendError.httpError(statusCode: httpResponse.statusCode)
        }
        
        let decoder = JSONDecoder()
        return try decoder.decode(ScanHistory.self, from: data)
    }
    
    // MARK: - System Stats
    func fetchSystemStats() async throws -> SystemStats {
        let url = URL(string: "\(baseURL)/stats")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BackendError.httpError(statusCode: httpResponse.statusCode)
        }
        
        let decoder = JSONDecoder()
        return try decoder.decode(SystemStats.self, from: data)
    }
    
    // MARK: - Health Check
    func healthCheck() async throws -> Bool {
        let url = URL(string: "\(baseURL)/health")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            return false
        }
        
        // Parse response to check if system is healthy
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let status = json["status"] as? String {
            return status == "healthy"
        }
        
        return false
    }
    
    // MARK: - Client Configuration
    func fetchClientConfig() async throws -> ClientConfig {
        let url = URL(string: "\(baseURL)/config")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BackendError.httpError(statusCode: httpResponse.statusCode)
        }
        
        let decoder = JSONDecoder()
        return try decoder.decode(ClientConfig.self, from: data)
    }
    
    // MARK: - Export
    func downloadExport() async throws -> Data {
        let url = URL(string: "\(baseURL)/export")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BackendError.httpError(statusCode: httpResponse.statusCode)
        }
        
        return data
    }
}

// MARK: - Errors
enum BackendError: Error, LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError
    case networkError
    
    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let statusCode):
            return "HTTP error: \(statusCode)"
        case .decodingError:
            return "Failed to decode response"
        case .networkError:
            return "Network connection error"
        }
    }
}
