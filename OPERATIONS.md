# Build and configure

These are deployment examples, not a record of a particular machine. Replace
`OWNER/REPOSITORY` and the `/Users/runner` host path before deployment. The
public infrastructure repository has no active self-hosted workflow. Register
workers for the consuming project and run only trusted code on them; fork PR
checks should use GitHub-hosted workers with external workflow approval retained.

## Build the manager and Mac app

```sh
just build-manager
just build-macos-app 'YOUR CODE SIGNING IDENTITY'
```

`components.toml` records the upstream revision and virtualization component.
Build outputs go under `build/`; downloaded source stays in ignored
`ephemeral/reference/`. The small icon drawing and ServiceManagement bridge are
compiled locally. Do not commit private signing identities or credentials.

Edit the embedded LaunchAgent's installation paths before building/signing.
Install the resulting signed app in the operator's Applications folder. Its
runtime config and data must remain outside the app and source checkout.
Validate the configuration and verify the installed signature before registration.
Signing does not imply notarization.

The installed `github-actions-runner-service` bridge accepts `register`,
`unregister` and `status`. Registration uses SMAppService; inspect its approval
status and the actual System Settings → General → Login Items & Extensions
entry. A LaunchAgent starts on user login, not before login as a system daemon.
Unregister requests termination and returns before the service is reaped.
Wait for the manager to exit before replacing the app; perform idle re-registration
before relying on busy-job draining or update behavior.

Install Tart from its official distribution. Set `TART_HOME` to the declared
internal CI root for every manual Tart operation; configure the same root in
TOML. Prepare an unregistered golden VM with the supported GitHub runner at
`/Users/admin/actions-runner`. Keep signing credentials out of the base.
Clones should share blocks on the same internal APFS filesystem. Before adopting
real workloads, provision the Go toolchain those workflows require into the
runner's `_work/_tool/go/<version>/arm64` cache and create `arm64.complete` beside
that directory. Obtain archives and SHA-256 checksums from go.dev. This lets
`actions/setup-go` reuse the installed toolchain in successive clean clones.
Verify that the base is unregistered before stopping it and allowing new clones.
A local base image still needs a measured size and update policy.

For Developer ID signing, install the matching Apple intermediate certificate
from [Apple PKI](https://www.apple.com/certificateauthority/) in the base's system
keychain. A P12 containing only the leaf certificate and private key can import
successfully while yielding no valid code-signing identity on a clean VM. Keep
private keys in the job's temporary keychain, never in the golden image.

## Linux service and caches

Build `images/linux/Dockerfile` and serve the local image from a loopback-only
registry, or configure another deliberately chosen image source. The example
registry unit binds `127.0.0.1:15000` and stores data under the owned CI root.
Install binaries, config and credentials under the explicit `/srv/` tree shown
in the units. The service uses installed binaries, not a developer checkout.

Install the user units under the service account's systemd configuration. User
manager lingering is required for operation without an interactive login.
`systemctl --user start`, `stop`, `status`, `enable` and `disable` control the
named service and timer. Verify the intended startup scope before enabling it.

The Docker workers have no independent restart policy or host socket mount.
The example ceilings are four Linux workers and two Mac VMs, with zero idle
workers. Set these explicitly for available host resources; CPU/memory/process
limits apply separately to each worker. Both examples provide 4 CPUs and
8 GiB per worker. A migration must preserve the replaced fleet's parallel job
count and existing CPU/RAM limits; increase capacity when changing that baseline. Create the three named
local-driver volumes as bind mounts from the owned cache directories:

| Host category | Worker mount | Policy |
| --- | --- | --- |
| `caches/go-mod` | `/cache/go-mod` | Go module downloads |
| `caches/go-build` | `/cache/go-build` | Rebuildable Go objects |
| `caches/pnpm` | `/cache/pnpm` | Package store and resolution metadata |

The image runs as uid 1001; cache ownership must permit that account to write.
Both `PNPM_CONFIG_STORE_DIR` and `PNPM_CONFIG_CACHE_DIR` are needed for pnpm
12 offline reuse. Application dependencies stay inside the disposable workspace.

Install `scripts/fleet.py` under the CI root's `bin/` directory on each host.
Adapt `examples/host.json` to declare the manager, supporting services, native
runners, cache paths and log retention. Keep private configuration outside the
source checkout. Python 3.11 or newer is required for the operator command.

The sample 2 GB/2 GB/1 GB cache budgets only warn. Weekly reset is retention,
not an enforced capacity limit. The generic disk guard remains disabled because
its pressure cleanup can affect global Docker storage. Do not enable global
pruning on an engine shared with unrelated services.

## Logs, secrets and proof

Provide credentials through restricted local files or the manager's environment
resolution; tracked TOML contains only `env:RUNNER_TOKEN` placeholders. Keep
private configs mode 600. Only per-job JIT registration enters disposable workers.

The example Mac config writes the manager's rotating log under the owned root:
10 MiB with one backup. Launchd console duplicates go to `/dev/null`. Diagnose
errors before log initialization using config validation or a foreground run.
Linux uses its rotating file plus the host's system journal; configure journal
retention separately. Tart OCI/IPSW cache cleanup does not cap local VMs.

Copy `examples/workflows/poc.yml` into a controlled qualification repository's
`.github/workflows/` directory, adapt labels/config, and dispatch trusted code.
The default scenario asserts distinct successive runners, clean HOME state,
Linux offline Go/package cache reuse, and Mac compilation/ad-hoc signing and
execution. The failure scenario intentionally exits 1 on both platforms. The
cancellation scenario waits for an operator to cancel the run after both jobs
start. Inspect owned VM/container storage afterward; successful GitHub steps
alone do not prove disposal.

Keep proof output and operational inventories in the private execution repository
or an appropriate private artifact store. For the first delivery, qualify the existing project's actual build and test
workflows, plus its signed packaging if used. Retire only workers whose workloads
have moved successfully. Further cache sharing, hard quotas and broader failure
simulation are separate improvements rather than an open-ended delivery gate.

## Multiple projects on one host

Use one manager with multiple `[[scaleset]]` entries, as shown in
`examples/linux-fleet.toml` and `examples/macos-fleet.toml`. Each entry registers
with its own consuming repository; workflows select its scale-set name with
`runs-on`. Keep per-project worker counts and CPU/RAM settings explicit. Set
the process-wide `concurrent` limit to accommodate the combined fleet rather
than retaining the limit from the first project migrated.

Linux scale sets inherit the three shared caches. They are intended for trusted
projects sharing a host. A private evaluator that retains evidence or needs host
authentication must keep that state and access boundary when ordinary CI moves;
do not discard its journals with a job workspace.

Mac projects can select different golden VMs. Native app packaging needs a base
with full Xcode selected, its license accepted and first-launch components
installed. Keep release credentials out of both bases. Wait for GitHub jobs to
finish before replacing a configuration or app; an idle health counter alone
does not establish that no job is running.

The pinned manager permits at most two running Tart VMs per Mac, shared across
all scale sets. Raising `concurrent` does not increase that limit. A migration
from more than two native Mac workers must retain native capacity or use another
Mac; do not silently serialize the existing workloads into two VM slots.

## Native workers and one fleet maintenance task

Use a host manifest for every installed runner. Docker/Tart scale sets are read
from the manager configuration; native runners are declared alongside them.
They keep their GitHub repository, labels, concurrency, credentials and existing
job commands when moved below `CI_ROOT/native/`. Private qualification workspaces
retain their reports and publication journals. Declare only rebuildable paths as
`cache_paths`; do not declare the evidence directory itself as a cache.

On Linux, `fleet.py HOST_JSON install-native` installs the declared systemd user
units. The installed script execs GitHub's runner; systemd handles restarts. Use
`platforms/linux/github-actions-runner-arm64-emulation.service` when ARM64 Linux
containers run on an x64 host, and set `platform = "linux/arm64"` on their scale
set. Build and push the worker image for that architecture. Preserve its CPU/RAM
and add its slot to the manager's combined concurrency limit.

On Mac, native execution must be attributed to **GitHub Actions Runner.app**.
The app embeds both the manager and a compiled native runner entry point, each
registered through SMAppService. Adapt both embedded plists before signing.
The native plist selects a host manifest and native runner name. A native entry's
service has `kind: "smappservice"`, the installed `bridge` path, `agent: "native"`
and label `com.tylergannon.github-actions-runner.native`. The manager selects
`agent: "manager"`. The bridge accepts `register`, `unregister` and `status`
with either service selector. Do not register Python, a shell, or an independent
LaunchAgent: macOS would attribute that background item to the interpreter.
Verify the installed signature and launchd's parent bundle identifier, as well
as the app name shown in Login Items & Extensions.

Copy `examples/fleet.json` outside the checkout and point it at each host manifest.
Native Docker-building jobs should select a dedicated BuildKit builder through
`BUILDX_BUILDER`, created with `docker buildx create --name github-actions-runner
--driver docker-container --driver-opt default-load=true --bootstrap`. Declare
its scoped `docker buildx prune --builder github-actions-runner --all --force`
command in `cache_commands`. Explicit `image_retention` repository prefixes can
expire old job image tags without pruning unrelated images or shared engines.

The same operator command covers local and SSH hosts:

```sh
python3 CI_ROOT/bin/fleet.py CI_ROOT/config/fleet.json status
python3 CI_ROOT/bin/fleet.py CI_ROOT/config/fleet.json maintain
```

Schedule **one** fleet maintenance invocation. Disable superseded per-runner
cleanup timers and the manager's Tart periodic cache cleanup when this task owns
it. Each host manifest can declare the scoped Tart cache command with its
`TART_HOME`; retain golden VMs. Do not run daemon-wide Docker pruning.

Maintenance temporarily removes native custom routing labels, waits for existing
native jobs and a quiet period with no active GitHub jobs in consuming
repositories, then drains/stops the managers and native services, resets caches and
retains 14 days of native diagnostics by default. Current workflows must select
native runners by their custom labels. Manager drain and native-service stop
windows must exceed the longest job timeout; the examples allow 100 minutes
for the existing 90-minute ARM64 release workload. Previously active services and routing
labels are restored even when cleanup fails. Services that were stopped stay
stopped. The host records its last result under `CI_ROOT/maintenance.json`.
Caches owned by container uid 1001 are cleared by a networkless Docker helper
mounted only on that host's CI root. Symlink escapes and deleting the whole root
are refused. Logs are limited to 10 MiB per file by default at maintenance.

The scheduled task should run maintenance, inspect fleet status and disk space,
and remain quiet on unchanged healthy state. Report failed cleanup, service
failure or unexplained growth. Private evidence remains visible storage with its
own deliberate retention decision; it must never be swept as a disposable cache.
