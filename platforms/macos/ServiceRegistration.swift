import Foundation
import ServiceManagement

// Native registration only. The unchanged upstream manager owns all runners.
@main
struct ServiceRegistration {
    static func main() {
        let service = SMAppService.agent(
            plistName: "com.tylergannon.github-actions-runner.poc.plist")
        do {
            switch CommandLine.arguments.dropFirst().first ?? "status" {
            case "register": try service.register()
            case "unregister": try service.unregister()
            case "status": break
            default:
                throw NSError(domain: "GitHubActionsRunner", code: 64,
                    userInfo: [NSLocalizedDescriptionKey:
                        "Usage: github-actions-runner-service [register|unregister|status]"])
            }
            switch service.status {
            case .enabled: print("GitHub Actions Runner: enabled")
            case .notRegistered: print("GitHub Actions Runner: not registered")
            case .requiresApproval: print("GitHub Actions Runner: requires approval in System Settings")
            case .notFound: print("GitHub Actions Runner: service not found")
            @unknown default: print("GitHub Actions Runner: unknown service status")
            }
        } catch {
            FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
