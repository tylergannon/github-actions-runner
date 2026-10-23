import Foundation
import ServiceManagement

// Native registration only. launchd owns both embedded execution services.
@main
struct ServiceRegistration {
    static func main() {
        do {
            let arguments = Array(CommandLine.arguments.dropFirst())
            let selection = arguments.count > 1 ? arguments[1] : "manager"
            let plist: String
            switch selection {
            case "manager": plist = "com.tylergannon.github-actions-runner.poc.plist"
            case "native": plist = "com.tylergannon.github-actions-runner.native.plist"
            default: throw NSError(domain: "GitHubActionsRunner", code: 64,
                userInfo: [NSLocalizedDescriptionKey: "Unknown service: \(selection)"])
            }
            let service = SMAppService.agent(plistName: plist)
            switch CommandLine.arguments.dropFirst().first ?? "status" {
            case "register": try service.register()
            case "unregister": try service.unregister()
            case "status": break
            default:
                throw NSError(domain: "GitHubActionsRunner", code: 64,
                    userInfo: [NSLocalizedDescriptionKey:
                        "Usage: github-actions-runner-service [register|unregister|status] [manager|native]"])
            }
            switch service.status {
            case .enabled: print("GitHub Actions Runner (\(selection)): enabled")
            case .notRegistered: print("GitHub Actions Runner (\(selection)): not registered")
            case .requiresApproval: print("GitHub Actions Runner (\(selection)): requires approval in System Settings")
            case .notFound: print("GitHub Actions Runner (\(selection)): service not found")
            @unknown default: print("GitHub Actions Runner (\(selection)): unknown service status")
            }
        } catch {
            FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
