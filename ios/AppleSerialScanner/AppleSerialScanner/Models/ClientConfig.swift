import Foundation

struct ClientConfig: Codable, Hashable {
    let version: String
    let minSupportedVersion: String
    let maintenanceMode: Bool
}