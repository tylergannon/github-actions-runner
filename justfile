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
    cp '{{root}}/ephemeral/reference/runscaler/LICENSE' '{{root}}/build/GitHub Actions Runner.app/Contents/Resources/runscaler-LICENSE'
    swiftc -parse-as-library -O -target arm64-apple-macosx13.0 '{{root}}/platforms/macos/ServiceRegistration.swift' -o '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner-service'
    codesign --force --options runtime --timestamp --sign '{{identity}}' '{{root}}/build/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner'
    codesign --force --options runtime --timestamp --sign '{{identity}}' '{{root}}/build/GitHub Actions Runner.app'
    codesign --verify --deep --strict '{{root}}/build/GitHub Actions Runner.app'

# Inspect the installed native service and its current GitHub capacity.
status-bob:
    ssh bob 'systemctl --user status github-actions-runner-poc.service --no-pager; /srv/github-actions-runner-poc/bin/github-actions-runner status --config /srv/github-actions-runner-poc/config/runner.toml'

caches-bob:
    ssh bob '/srv/github-actions-runner-poc/bin/github-actions-runner cache --config /srv/github-actions-runner-poc/config/runner.toml'

# Drains the PoC worker, clears only its three caches, then starts it again.
clean-caches-bob:
    ssh bob 'systemctl --user start github-actions-runner-poc-cache-cleanup.service'

storage-macos:
    du -h -d 2 /Users/tyler/CI/github-actions-runner
    df -h /Users/tyler/CI/github-actions-runner

stop-bob:
    ssh bob 'systemctl --user stop github-actions-runner-poc.service'

start-bob:
    ssh bob 'systemctl --user start github-actions-runner-poc.service'

status-macos:
    '/Users/tyler/Applications/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner-service' status
    launchctl print 'gui/501/com.tylergannon.github-actions-runner.poc'

vms-macos:
    env TART_HOME='/Users/tyler/CI/github-actions-runner/tart' '/Users/tyler/Applications/Tart.app/Contents/MacOS/tart' list

stop-macos:
    '/Users/tyler/Applications/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner-service' unregister

start-macos:
    '/Users/tyler/Applications/GitHub Actions Runner.app/Contents/MacOS/github-actions-runner-service' register
