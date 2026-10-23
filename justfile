root := justfile_directory()
manager_revision := "60ced08cbc3c6b52f728c87fbdbd225977ce9189"

# Build the unchanged upstream manager with a recognizable executable name.
build-manager:
    mkdir -p '{{root}}/build' '{{root}}/ephemeral/reference'
    test -d '{{root}}/ephemeral/reference/runscaler/.git' || git clone https://github.com/ysya/runscaler.git '{{root}}/ephemeral/reference/runscaler'
    git -C '{{root}}/ephemeral/reference/runscaler' fetch --depth 1 origin '{{manager_revision}}'
    git -C '{{root}}/ephemeral/reference/runscaler' checkout --detach '{{manager_revision}}'
    CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go -C '{{root}}/ephemeral/reference/runscaler' build -o '{{root}}/build/github-actions-runner-darwin-arm64' ./cmd/runner
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go -C '{{root}}/ephemeral/reference/runscaler' build -o '{{root}}/build/github-actions-runner-linux-amd64' ./cmd/runner

# Compile the small Apple registration bridge and sign the owning app bundle.
build-macos-app identity:
    mkdir -p '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS' '{{root}}/build/GitHub Actions Runner.app/Contents/Library/LaunchAgents' '{{root}}/build/GitHub Actions Runner.app/Contents/Resources'
    cp '{{root}}/build/github-actions-runner-darwin-arm64' '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner'
    cp '{{root}}/platforms/macos/Info.plist' '{{root}}/build/GitHub Actions Runner.app/Contents/Info.plist'
    cp '{{root}}/platforms/macos/com.tylergannon.github-actions-runner.poc.plist' '{{root}}/build/GitHub Actions Runner.app/Contents/Library/LaunchAgents/'
    cp '{{root}}/platforms/macos/com.tylergannon.github-actions-runner.native.plist' '{{root}}/build/GitHub Actions Runner.app/Contents/Library/LaunchAgents/'
    cp '{{root}}/ephemeral/reference/runscaler/LICENSE' '{{root}}/build/GitHub Actions Runner.app/Contents/Resources/runscaler-LICENSE'
    swift '{{root}}/platforms/macos/MakeIcon.swift' '{{root}}/build/RunnerIcon.iconset'
    iconutil --convert icns '{{root}}/build/RunnerIcon.iconset' --output '{{root}}/build/GitHub Actions Runner.app/Contents/Resources/RunnerIcon.icns'
    swiftc -parse-as-library -O -target arm64-apple-macosx13.0 '{{root}}/platforms/macos/ServiceRegistration.swift' -o '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner-service'
    swiftc -parse-as-library -O -target arm64-apple-macosx13.0 '{{root}}/platforms/macos/NativeRunner.swift' -o '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-native-runner'
    codesign --force --options runtime --timestamp --sign '{{identity}}' '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner'
    codesign --force --options runtime --timestamp --sign '{{identity}}' '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-native-runner'
    codesign --force --options runtime --timestamp --sign '{{identity}}' '{{root}}/build/GitHub Actions Runner.app'
    codesign --verify --deep --strict '{{root}}/build/GitHub Actions Runner.app'
