# Operating the isolated runner PoC

The PoC runs only jobs for this private repository. Existing skgo, Gimbal and
skgo-project runners remain in place. Do not retire them based on this proof.
The accepted requirements are in [DESIGN.md](DESIGN.md); the older fleet
inventory is [CURRENT.md](CURRENT.md).

## Installed homes and controls

| Host | Installed software and data | Native controls |
| --- | --- | --- |
| Mac | `~/Applications/GitHub Actions Runner.app`; internal data `~/CI/github-actions-runner/` | `just start-macos`, `just stop-macos`, `just status-macos`; `just restart-macos` when idle |
| Bob | `/srv/github-actions-runner-poc/{bin,config,secrets,caches,registry,images,artifacts,logs}` | `just start-bob`, `just stop-bob`, `just status-bob` |

Both managers scale from zero to one worker. The Mac uses a 4 vCPU, 4096 MiB
Tart clone for each job; Bob uses a 2 CPU, 4096 MiB, 1024-process Docker worker.
Workers have disposable HOME/workspace state. Linux jobs do not receive the
host Docker socket. This PoC does not qualify Docker-using application jobs.

Mac registration uses Apple's SMAppService and an embedded LaunchAgent. System
Settings → General → Login Items & Extensions displays **GitHub Actions Runner**.
The app is Developer ID signed with team `6H59L2SRR6`, includes an icon, and is
not notarized. A LaunchAgent starts after the user logs in, rather than as a
system daemon before login. Logout/reboot behavior still needs qualification.
Unregister requests termination and returns before the process is reaped;
allow shutdown to finish before replacing installed files. The observed
launchd termination allowance is 60 seconds; busy-job draining is not proved.

The source checkout is not an installed runtime dependency. Build with
`just build-manager` and `just build-macos-app 'Developer ID Application: Tyler Gannon (6H59L2SRR6)'`.
To update, stop the installed service, verify its process exited, copy the signed
app from `build/` into `~/Applications/`, verify its signature, then register it.
Config and credentials remain under the CI root, outside the app bundle.

## Images, tools and credentials

The manager revision and Tart archive checksum are in `components.toml`.
The installed Tart executable is `~/Applications/Tart.app/Contents/MacOS/tart`.
**Every manual Tart command must set**
`TART_HOME=/Users/tyler/CI/github-actions-runner/tart`; `just vms-macos` does this.
The manager gets the same root from its private TOML.

The stopped golden image is `github-actions-runner-poc-base`, a 50 GB logical
disk occupying roughly 33 GB before APFS clone sharing. Never register it as a
persistent runner or put signing credentials into it. Clone only on internal
APFS storage. Its provisioned disk SHA-256 is
`951cf675a330dbb89c0e991d57e2e61cc9842a3bca79c5aac9adb095713f4fb4`.
The source was `ghcr.io/cirruslabs/macos-tahoe-base:latest` at digest
`sha256:4aaa751fa7538902d73c767f27a066fc87e83f183069da4e4b5022863abd4c77`.
The unregistered runner in `/Users/admin/actions-runner` is version `2.338.1`,
archive SHA-256 `52c3fb801b931fbd454979bae5ec3443ea3da2c4a1b4c44fa546fb630d61a0a9`.
Guest access uses `tart exec`, without SSH setup.

Bob's locally built worker image is served at
`localhost:15000/github-actions-runner-poc:local`; the manager pulls it at startup.
The registry binds only loopback. Its data is part of the owned PoC root.
Use Node **24** and Vite+ (`vp install`, `vp run`, `vp exec`, `vp dlx`);
record resolved patches in diagnostics. Keep GitHub's bundled Node runtimes.
Go is `1.27` in the Linux image; the current Mac base does not yet include Go.

Do not print or commit credentials. Bob uses mode-600
`secrets/service.env`; Mac uses mode-600
`poc/config/runner.private.toml`. Tracked configs have `env:RUNNER_TOKEN`
placeholders. Only per-job JIT registration enters disposable workers.

## Storage and maintenance

`just storage-macos` reports the owned root and internal free space.
`just caches-bob` reports the Linux cache categories. Docker engine image/layer
storage is accounted separately from bind mounts; the shared Bob daemon also
owns unrelated media services. Never globally prune it.

Linux's three named volumes bind `caches/go-mod`, `caches/go-build`, and
`caches/pnpm` to `/cache/go-mod`, `/cache/go-build`, and `/cache/pnpm`.
The worker uid is 1001. For pnpm 12, both
`PNPM_CONFIG_STORE_DIR=/cache/pnpm/store` and
`PNPM_CONFIG_CACHE_DIR=/cache/pnpm/metadata` are necessary for offline reuse.
Project dependencies such as `node_modules` stay inside disposable workspaces.

`just clean-caches-bob` invokes a native oneshot: drain/stop the manager,
empty exactly these caches using a networkless helper, then restart the
manager on success or failure. The accompanying timer is Sunday 11:00 UTC
(05:00 Costa Rica), randomized up to 30 minutes, with persistent catch-up.
The units are installed but remain disabled at boot; enable the manager,
registry and cleanup timer together before leaving the PoC unattended.

Configured Linux cache budgets of 2 GB/2 GB/1 GB are warning thresholds,
**not enforced quotas**. Weekly full reset is retention, not instantaneous
capacity protection. The manager's generic disk guard remains disabled:
it can reclaim global Docker storage on Bob despite routine prune switches
being off. Do not enable it on the shared daemon without resolving that scope.

Tart OCI/IPSW cache retention runs every six hours with seven-day age and
8 GB budget. It does not cap local golden images or growing job clones.
The upstream provider does not expose shared guest directory mounts, so Mac
Go/package cache sharing remains incomplete. Stopped copies on the external
backup volume are unused; never run from them or remove unrelated backups.

Mac manager diagnostics use `poc/logs/runner.log`, rotating at 10 MiB with
one backup through the existing manager. Launchd's duplicate console output
goes to `/dev/null`; errors before log initialization require running the
manager's `validate` command or foreground diagnostics. Old stdout/stderr files
from the initial experiment are no longer written. Bob uses its rotating
`logs/runner.log` and the system journal; journal retention is host policy.

## Reproducing proof

With both managers started:

```sh
gh workflow run poc.yml --repo tylergannon/github-actions-runner --ref main -f scenario=proof
gh run list --repo tylergannon/github-actions-runner --workflow poc.yml --limit 5
```

The proof asserts distinct successive runner names, fresh HOME state, Linux
Go/package cache reuse with network lookup disabled, and macOS compilation,
ad-hoc signing, signature verification and execution. Inspect host disposal
with `just vms-macos` and scoped Docker container listing after completion.
GitHub job success alone does not establish deletion.

Dispatch `scenario=failure` for deliberate exit-1 jobs on both platforms;
those runs must be red. Dispatch `scenario=cancellation`, wait for both jobs
to execute the lifecycle step, then cancel that run by ID and inspect disposal.
These scenarios are manual and do not run on PRs. Use the tested branch as
`--ref` when validating changes, and qualify the final source SHA.

## Evidence and production boundary

[Run 39871482145](https://github.com/tylergannon/github-actions-runner/actions/runs/39871482145)
passed all four jobs at `08624fde1a0029a22933b31bc5b8695ba18d2246`.
The Mac compiled, signed and ran a C binary in a guest, then a second guest
had no prior HOME marker. Both clones disappeared from the owned Tart root.
Linux repeated its offline cache-reuse proof. Native app registration,
unregistration, idle restart and signed bundle replacement were exercised.
System Settings visibly displayed the owning app name and background activity.

The pinned manager can misclassify a very short successful Mac job as a startup
failure during its five-second settling observation. The original jobs still
passed and their clones were removed. Current proof jobs remain alive for ten
seconds to exercise the normal tracked lifecycle. This is an upstream defect,
not a general fix for short jobs.

Before production migration, resolve enforced per-category storage budgets and
admission control; Mac shared caches and toolchains; signing-secret delivery
and real release jobs; bounded artifact export/retention; cleanup of nested
Docker qualification workloads; busy stop, crash, logout and reboot behavior;
and the short-job manager defect. Choose final worker counts from measured
queue/use data. Then migrate consumers incrementally while preserving labels,
repository/private qualification boundaries and credentials. The old mountless
skgo-project containers may hold state in writable layers: do not casually
recreate them. No production fleet migration has been performed.
