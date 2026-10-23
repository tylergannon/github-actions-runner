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

The cleanup oneshot stops the manager before emptying exactly those three
caches using a networkless helper, then restarts the manager on success or
failure. Its weekly timer has randomized delay and persistent catch-up. Enable
maintenance deliberately alongside an unattended manager.

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

## Weekly operation

Enable the native Linux cache-reset timer with the installed manager and registry.
It drains the manager before resetting the three owned caches. On Mac, the
manager's existing Tart cache maintenance runs periodically; job clones are
removed after use. Keep its rotating log under the owned root.

Schedule a weekly operational check after cache maintenance. Inspect both native
services and health endpoints, free disk space, cache/image/log usage and the last
maintenance result. Alert only for a failed service or maintenance run, low disk
space, or material unexplained accumulation; healthy runs should remain quiet.
Count idle zero-capacity operation as normal. Do not globally prune a shared
Docker engine or delete active workers to satisfy a storage target.

The example cache thresholds warn rather than enforce hard quotas. This delivery
uses scoped scheduled cleanup and a weekly exception check; it does not claim
fail-closed storage admission.
