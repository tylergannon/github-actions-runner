# Build and configure

These are deployment examples, not a record of a particular machine. Replace
`OWNER/REPOSITORY` and the `/Users/runner` host path before deployment. The
public repository has no active self-hosted workflow; use a private qualification
repository and register its workers there.

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
Clones should share blocks on the same internal APFS filesystem. A local base
image still needs an independent disk budget and update policy.

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
CPU/memory/process limits are in the example TOML. Create the three named
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

Copy `examples/workflows/poc.yml` into the private qualification repository's
`.github/workflows/` directory, adapt labels/config, and dispatch it there.
The default scenario asserts distinct successive runners, clean HOME state,
Linux offline Go/package cache reuse, and Mac compilation/ad-hoc signing and
execution. The failure scenario intentionally exits 1 on both platforms. The
cancellation scenario waits for an operator to cancel the run after both jobs
start. Inspect owned VM/container storage afterward; successful GitHub steps
alone do not prove disposal.

Keep proof output and operational inventories in the private execution repository
or an appropriate private artifact store. Shared Mac caches, Go provisioning,
release-signing credential delivery, enforced storage admission, artifact retention
and interruption/reboot cleanup remain prerequisites for production adoption.
