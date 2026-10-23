import Foundation
import Darwin

// A signed, app-owned launch entry point. It replaces itself with GitHub's
// runner; launchd supplies lifecycle management, not a Python background agent.
@main
struct NativeRunner {
    struct Host: Decodable { let root: String; let native: [Runner] }
    struct Runner: Decodable {
        let name: String
        let directory: String
        let command: [String]
        let environment: [String: String]
    }

    static func main() {
        do {
            guard CommandLine.arguments.count == 3 else {
                throw failure("Usage: github-actions-native-runner HOST_JSON NAME")
            }
            let host = try JSONDecoder().decode(Host.self,
                from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
            guard let runner = host.native.first(where: { $0.name == CommandLine.arguments[2] }),
                !runner.command.isEmpty else { throw failure("Native runner is not declared") }
            let root = URL(fileURLWithPath: host.root).resolvingSymlinksInPath()
            let directory = root.appendingPathComponent(runner.directory).resolvingSymlinksInPath()
            guard directory.path.hasPrefix(root.path + "/") else {
                throw failure("Native runner directory escapes the CI root")
            }
            for (key, value) in runner.environment { setenv(key, value, 1) }
            guard chdir(directory.path) == 0 else { throw failure("Cannot enter native runner directory") }
            let arguments = runner.command.map { strdup($0) } + [nil]
            defer { for argument in arguments { free(argument) } }
            arguments.withUnsafeBufferPointer { buffer in
                _ = execvp(runner.command[0], buffer.baseAddress!)
            }
            throw failure("Cannot execute native runner: \(String(cString: strerror(errno)))")
        } catch {
            FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }

    static func failure(_ message: String) -> NSError {
        NSError(domain: "GitHubActionsRunner", code: 1,
                userInfo: [NSLocalizedDescriptionKey: message])
    }
}
