# Native runner services

**Proposal, 2026-10-22.** This records a design for discussion, not permission
to replace the running fleet. [CURRENT.md](CURRENT.md) records the inspected
installations separately.

## Desired state

An operator can identify every runner's purpose, repository, host, service,
files, tools and logs without searching application repositories or decoding
a shell script's name. The native operating system service manager starts,
stops and supervises each instance. This repository explains and reproduces
the installed configuration on both hosts.

The public executable is `github-actions-runner`. The macOS application's
name is **GitHub Actions Runner.app**. There is one OS service per worker,
with a stable instance ID carried through its configuration, logs, data
directory and GitHub registration. Worker count is an explicit host setting;
installation never silently adds another worker.

## Ownership

| Owner | Responsibility |
| --- | --- |
| This repository | Native packaging, OS units, host/instance definitions, runner distribution, shared tool policy and migration |
| Application repository | Workflow, build/test commands, frontend dependencies and an actual demonstrated tool exception |
| OS service manager | Launch at the declared time, stop, crash restart and service status |
| GitHub runner | GitHub protocol, assignment and execution of jobs |
| Tool manager | Resolve and install shared build tools |

The compiled program is a small service adapter and administration CLI. It
loads one instance definition, starts its declared execution environment,
forwards output, waits for it, and participates in shutdown. It does not have
its own background scheduler, detached daemon or restart loop. There is no
custom CI engine, database or web dashboard.

GitHub's supported runner package remains intact. Its internal `runsvc.sh`
entry point may still be invoked inside the service. It is an upstream
implementation detail, never our installed service identity. Renaming that
script or disguising its argv is insufficient.

## Repository and installation boundary

The proposed source tree is small:

```text
cmd/github-actions-runner/       compiled administration CLI and service adapter
platforms/macos/                app metadata, ServiceManagement bridge, agents
platforms/linux/                systemd service template and aggregate target
hosts/amritanandamayi.toml      declared Mac instances and tool policy
hosts/bob.toml                 declared Linux instances and execution profiles
images/linux/                  Linux build environment and ARM64 variant
```

These are proposed implementation locations; the design branch does not
pretend to contain runnable packaging yet. Existing application-specific
runner deployment files move here as each migration is accepted. Applications
retain only the workflow labels and build requirements they consume.

Installed executables and definitions are deployed from a known repository
revision into stable OS locations. Services never depend on the current
branch, uncommitted files or existence of a developer checkout. Local
credentials and job output are never committed.

Every installed instance records the source revision, upstream runner version,
repository scope, registration name, labels, execution architecture, runtime
kind, paths and configured resource budget. Reports distinguish desired tool
requests from the actual installed versions.

## macOS: an application with registered launch agents

Package a real, consistently signed application, installed at
`~/Applications/GitHub Actions Runner.app`. Its executable is
`Contents/MacOS/github-actions-runner`, its bundle identifier is
`com.tylergannon.github-actions-runner`, and its bundle name and display name
are both `GitHub Actions Runner`. Include an application icon.

Embed one launch-agent plist per configured instance in
`Contents/Library/LaunchAgents`. Register and unregister them through
`SMAppService.agent(plistName:)`, Apple's current ServiceManagement API.
Use a native framework bridge where required by the compiled implementation.
Set `BundleProgram` to the bundled executable and give each agent a label
such as `com.tylergannon.github-actions-runner.skgo-1`. Each agent receives
its instance ID explicitly. The app bundle is the owning application;
merely writing a friendly `Label` into an external plist is insufficient.

This is a per-user launch agent because the existing macOS work includes
signing and user-session tools. It starts with the user's session. A system
LaunchDaemon would change that execution model and is not the default.

Use `~/Library/Application Support/GitHub Actions Runner/` for instance
configuration and registration state, `~/Library/Caches/GitHub Actions
Runner/` for disposable workspaces, and `~/Library/Logs/GitHub Actions
Runner/<instance>/` for rotated upstream/job diagnostics. Lifecycle messages
also use a stable Unified Logging subsystem with the instance ID.

Use the OS's approval state faithfully: report enabled, disabled or requiring
approval. Never report successful installation as proof of permission or
online status, and never undo a user's disable action automatically.

The naming requirement is an acceptance criterion, not an assumption about
plist fields. Inspect the installed item in System Settings > General >
Login Items & Extensions, including its information panel. It must identify
the owning application and launch the correct instance. Test the app's
signing/attribution and updates on the actual host before claiming success.

## Linux: native systemd instances on Bob

Bob runs Arch Linux with systemd. Its existing `tyler` user manager has
`Linger=yes`, so a proper user service can start at boot without an interactive
login. Retain that execution identity for the first migration; changing the
account is a separate ownership and cache-permission decision.

Install `github-actions-runner@.service` under
`~/.config/systemd/user/`, with an aggregate `github-actions-runners.target`.
An instance such as `github-actions-runner@skgo-1.service` has description
`GitHub Actions Runner - skgo-1` and executes the installed native binary
directly, for example:

```ini
[Unit]
Description=GitHub Actions Runner - %i
PartOf=github-actions-runners.target

[Service]
Type=exec
ExecStart=%h/.local/bin/github-actions-runner serve --instance %i
ExecStop=%h/.local/bin/github-actions-runner stop-runtime --instance %i
Restart=on-failure
RestartSec=10s
TimeoutStopSec=150s
KillMode=control-group
SyslogIdentifier=github-actions-runner-%i

[Install]
WantedBy=github-actions-runners.target
```

This illustrates the service contract; executable paths and CLI are proposed.
The aggregate target starts with the user manager's default target. Status,
enable/disable, start/stop/restart and logs work through ordinary
`systemctl --user` and `journalctl --user -u` commands. Exits for invalid
configuration or revoked registration must not spin indefinitely. The
implementation must choose and document the corresponding exit policy.

Use `~/.config/github-actions-runner/` for installed definitions,
`~/.local/state/github-actions-runner/instances/<id>/` for registration state,
and `~/.cache/github-actions-runner/` for workspaces and rebuildable caches.
Journald owns service log retention; additional upstream diagnostic files
have explicit rotation. The installed binary is independent of the checkout.

### Container environment, native service ownership

Retain Ubuntu-based execution containers initially: current workflows already
use that environment, while Bob's host is Arch. Moving CI directly onto Arch
would be a separate compatibility change. A container does not replace the
need for a named, discoverable OS service.

Each systemd instance owns exactly one foreground container lifecycle.
Docker restart policy is disabled; systemd is the sole host restart owner.
The compiled adapter must stop and wait for its owned container on shutdown,
even if its attached Docker client has failed. Killing the client process
alone is not proof that the job stopped. It checks Docker readiness and
reports a bounded failure instead of waiting forever for a sentinel file.

Persist registration outside the container's writable layer. Job workspaces
remain per instance; images and suitable versioned tools/caches are shared
within a compatible execution profile. Image layers already share disk on
the same Docker host: starting several containers does not inherently copy
every image byte onto disk again.

Container CPU/memory limits apply to the job container, not just the host
adapter. Keep current budgets as inventory until capacity is reviewed.
ARM64 execution is an explicit emulated profile with a declared binfmt/QEMU
dependency and startup ordering; it must not be described as native ARM64.
Manage that prerequisite through a named unit in this repository too.

## Tools and disk lifecycle

Node is requested as **`24`** throughout the fleet. A major-version request
allows routine patch updates. Exact patch pins require an actual stated
constraint. The same version policy applies locally and in CI.

Use mise for shared build tool resolution in compatible profiles; keep Vite+
as the frontend package/build command surface. Consolidate overlapping
`setup-go`, `setup-node`, mise and Vite+ Node provisioning during migration so
each build tool has one installer/owner. Multiple same-profile workers reuse
the installed tool. Preserve an explicit distinction between build Node and
GitHub's bundled Node, which remains part of the upstream runner package.

Share by OS, architecture, environment compatibility and repository trust
boundary. An ARM64 Linux compiler installation is not the same executable as
the Mac or x86_64 Linux installation. Private qualification workspaces and
credentials remain separate; sharing tools must not expose private evidence
or holdout data to application jobs.

Updates happen as tool/environment maintenance, outside active jobs. Record
the concrete resolved versions for a job. Do not resolve a different patch
halfway through a build or turn a tool update into synchronized patch edits
across every repository. A shared tool installation must not be pruned while
in use. Application dependency lockfiles retain their own purpose.

Separate durable registration from disposable workspaces and rebuildable
caches. Successful release staging is removed after artifact publication;
failure diagnostics have a retention limit. Status reports explain disk
usage by category. Uninstall removes OS registration but preserves data
unless explicit data deletion is requested. No global Docker pruning.

## Migration and acceptance

Keep the existing fleet unchanged during design. Preserve skgo, Gimbal and
skgo-project as distinct repository scopes and preserve existing workflow
labels initially. Four older Bob containers are skgo-project workers, not
redundant skgo workers. Determine their live registrations and consumers
before proposing retirement. Worker counts remain a capacity decision; this
design does not silently adopt the previous suggestion to reduce them.

Prove one new macOS instance and one Bob instance before moving the rest.
Drain an old instance before replacement. Drain means it cannot acquire new
work and its accepted job has finished; a momentary GitHub `busy=false`
snapshot alone is insufficient. Preserve rollback state until the replacement
receives and completes an appropriate real job. Remove superseded OS units
and registrations only after confirming which instance owns which identity.

Acceptance is observed behavior:

- System Settings identifies **GitHub Actions Runner**, with the correct app,
  executable and approval state. Disable/enable and login startup work.
- systemd lists each instance with its purpose and journals; user-manager
  startup, OS stop/restart and Docker daemon recovery leave one intended
  container and no abandoned job processes.
- Crash recovery uses one restart authority. Explicit stop stays stopped;
  service removal does not resurrect it.
- Each migrated repository receives a real job through its preserved labels.
  A service PID is not evidence of a connected or correctly routed runner.
- Two compatible workers report the same shared build-tool installation.
  Application dependencies and private qualification state stay independent.
- Inspection explains where every installed definition, credential directory,
  workspace, log and tool came from, including the deployed source revision.

Before implementation, align on the proposed app identity, user-service
scope, retention policy and initial worker counts. The first implementation
must establish native service identity and lifecycle before fleet expansion.

## Platform references

- [Apple: SMAppService](https://developer.apple.com/documentation/servicemanagement/smappservice)
- [Apple: app installer and ServiceManagement](https://developer.apple.com/documentation/servicemanagement/updating-your-app-package-installer-to-use-the-new-service-management-api)
- [Apple: inspecting login and background items](https://support.apple.com/en-gb/guide/deployment/depdca572563/1/web/1.0)
- [systemd service semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Docker: host process managers and restart ownership](https://docs.docker.com/engine/containers/start-containers-automatically/)
- [GitHub: supported service entry point](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application#customizing-the-self-hosted-runner-service)
- [Mise: shared installed tools and separate state](https://mise.jdx.dev/directories.html)
