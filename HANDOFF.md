# GitHub Actions Runner: requirements, decisions and continuation

Updated 2026-10-22. Read this before continuing implementation.

## Where we are

We are replacing scattered, poorly identified self-hosted GitHub Actions runner
installations with a small, understandable infrastructure repository. The user
authorized continuing through a working proof of concept, then requested this
handoff so they can resume in a new project/session. **The full PoC is not yet
proved. Linux execution/cache reuse is proved; macOS execution is pending.**

The PoC is deliberately stopped for handoff. No production runner migration has
been performed. The previous external-drive choice was expressly rejected;
the usable macOS base image is now on the internal disk.

- Private repository: https://github.com/tylergannon/github-actions-runner
- Initial PoC PR: https://github.com/tylergannon/github-actions-runner/pull/1
- Repository and continuation directory: `/Users/tyler/src/github-actions-runner`.
- Branch: `main`, as explicitly requested by the user after this handoff.
- Latest implementation commit before this handoff: `5b6093e2f10277ed831c3a6c33ede15b05653161`.
- Original chat: `01a16587-fd0a-7600-bdb9-a9ba1f3033ab`, titled
  **Locate runner directories and runsvc**.

The user requested keeping this simple: the requirements, handoff and PoC
implementation belong together on `main` in the repository directory above.
The initial `codex/service-design` worktree is retired after merging. Start the
new project/session in the repository directory; no separate worktree is needed
to locate the implementation.

## Requirements and decisions from the conversation

These were reconstructed by reading the original session's user messages,
including the messages before compactions, and the responses they accepted or
corrected. Later user corrections take precedence over earlier suggestions.

### Ownership and maintainability

1. **Have a separate repository that owns the runner definitions.** The user
   initially asked why definitions were not in the application projects, then
   explicitly chose a new runner repository. Ownership must be discoverable;
   another collection of undocumented home-directory installations is unacceptable.
2. **Design something idiomatic and maintainable using existing implementations.**
   The user challenged inventing an already-solved problem. Configuration,
   packaging, images and native units are the core deliverables. Do not write
   another runner supervisor/controller merely to centralize configuration.
3. **Use legitimate native service integration on both operating systems.**
   launchd/Apple ServiceManagement on macOS; systemd on Bob. Native start, stop,
   status, enable/disable and startup behavior must be understandable and real.
   Opaque wrapper scripts and shell restart/sentinel loops are rejected.
4. **Identify the service properly to the OS and the user.** `runsvc.sh` is the
   motivating failure. The intended installed identity is **GitHub Actions Runner**,
   with descriptive executable/service names. On macOS, inspect the installed
   System Settings entry; renaming a plist Label is not proof. App metadata,
   signing and an icon belong to the finished package. The icon is still absent.
5. **Stable installations must not depend on a developer's mutable checkout.**
   The repository defines the installation; installed executables, credentials
   and runtime data have explicit homes. CI jobs get their own disposable checkout.
6. **Worker count is an explicit capacity choice.** The two original Mac skgo
   workers existed only for parallelism and had identical labels/capabilities;
   no measured queue-delay justification was found. Do not preserve duplication
   as a supposed compatibility requirement or promise a final fleet size yet.
   The PoC uses one worker at a time per host, scaling to zero when idle.

### Toolchains

7. **Declare Node as `24` consistently across the projects/fleet.** The user
   explicitly rejects automatically pinning every patch version. The earlier
   recommendation to standardize on one exact Node patch was corrected. Record
   resolved versions in diagnostics; normal patch updates should not require
   editing every application's workflow. Existing application declarations have
   not yet all been changed.
8. **Avoid needless independent Go/Node installations per persistent worker.**
   Container image layers or VM base-image clones share installed tools.
   Supporting several versions is not a reason to preserve unexplained drift.
   No user decision establishes an exact shared Go patch; the PoC uses Go `1.27`.
9. **Do not remove GitHub's bundled Node runtimes.** They execute JavaScript
   Actions independently of application/build Node. Earlier claims that all
   bundled copies were needless waste were corrected. Retain the supported runner
   distribution. Source revisions, artifact checksums and deliberate component
   provenance pins are distinct from the rejected routine Node patch pins.
10. **Keep Vite+ as the frontend command surface.** Use `vp install`, `vp run`,
    `vp exec`, `vp dlx`; do not directly invoke npm/pnpm in project commands.
    The implementation may contain pnpm's store because Vite+ uses it.

### Execution environments

11. **Linux CI runs in disposable Docker containers.** Keep the Ubuntu worker
    environment initially because Bob itself is Arch. Installed tools belong in
    a shared worker image. Set explicit CPU/memory/process limits.
12. **macOS CI runs in a fresh disposable macOS VM for each job.** The user
    explicitly accepted this option. This is settled: do not reopen direct host
    execution as an unresolved platform choice. Export selected results, stop
    the VM and delete its clone. Maintain a reusable base image.
13. **Docker on a Mac does not provide Darwin/Xcode/signing qualification.**
    macOS jobs need genuine macOS guests on Apple hardware. Keep signing secrets
    out of the reusable golden image; provision them for the relevant job.
14. **Keep repository routing and private qualification boundaries intact.**
    skgo, Gimbal and skgo-project have distinct consumers. Personal-account
    repositories must be supported, not just organization registrations. The
    private skgo-project core qualification runner is a separate consumer.
15. **One lifecycle authority per worker.** In the proposed setup the native
    service runs the existing manager, which creates/removes workers. Do not
    combine systemd restart with Docker's independent worker restart policy.
    Stop must handle actual children; startup must reconcile owned leftovers.

### Storage: a primary requirement, not cleanup polish

16. **Keep CI data in one obvious, owned parent tree.** The user's central
    objection was data being spread across arbitrary HOME/cache/temp locations.
    They explicitly agreed that several mounts under one parent are desirable.
    OS app bundles/service registrations may remain in normal native locations;
    that does not justify scattering job data around the host.
17. **Use a small number of purposeful, shared cache mounts.** Start with Go
    module downloads, Go build output, and the pnpm package store/metadata used
    by Vite+. Add another only for a demonstrated benefit. Separate cache
    lifetimes/budgets from job workspace and artifact lifetimes.
18. **Workspaces, temporary HOME directories and dependencies such as
    `node_modules` are per job and disposable.** Do not mount one permanent
    workspace and call it clean merely because a container was replaced. Share
    download/build caches, not mutable application dependency trees.
19. **Retain useful evidence, not entire scratch environments.** Qualification
    owns exporting meaningful results and removing per-attempt execution homes.
    Runner infrastructure owns shared caches and worker lifecycle. Frozen source
    archives do not make the original multi-gigabyte agent HOME useful evidence.
20. **Every persistent category needs an owner, visible usage, a budget and a
    removal rule.** Include Go/package caches, images/layers, Docker build cache,
    VM images/clones, artifacts and logs. Cleanup must cover success, failure,
    cancellation and interruption/reboot. A bind mount is not a disk quota.
21. **Maintenance must actually prevent accumulation.** The latest user request
    specifically requires remembering to pare back caches before they fill
    storage. We chose native scheduled cleanup plus inspection commands so the
    system does not depend only on human memory. Current PoC scheduling is a
    provisional implementation, not proof that hard limits are finished.
22. **macOS runner storage must be on the internal disk.** The user explicitly
    stopped the external-drive implementation. Do not return to the external
    backup volume even if internal capacity is tight. Make room first.
23. **Make the data location visibly part of our purview.** In response to the
    user's latest location correction, the working choice is
    `/Users/tyler/CI/github-actions-runner/`, rather than hiding runtime data in
    `~/Library/Application Support`. This exact spelling was an implementation
    choice offered in response; the requirement is visible, owned internal storage.
24. **Do not globally prune Bob's Docker daemon or disturb media.** It also
    runs unrelated services. Keep CI cleanup scoped to owned paths/containers.
    Account for Docker engine storage outside the CI bind-mount root rather than
    pretending every image byte physically lives beneath that root. A dedicated
    engine/storage domain remains an option if strict physical quotas require it.

### Delivery and communication

25. **Reach a working PoC before stopping implementation**, as originally
    authorized. The latest request pauses that work for this handoff/new session.
    Resume toward actual execution, not another design-only answer.
26. **Prove the running system.** Real GitHub jobs, successive fresh workers,
    cache reuse, disposal, native identity and native controls matter. A compile
    or metadata check alone does not establish those claims.
27. **Migrate incrementally only after qualification.** Preserve labels and
    credentials, prove replacement behavior, then retire predecessors. Do not
    casually delete the four older mountless skgo-project containers: state may
    reside in their writable layers. The PoC scope does not silently migrate them.
28. **Ask pointed questions when a genuine choice needs the user.** The user
    objected to vague announcements such as “the remaining platform decision is
    macOS.” Do not repeatedly ask permission for authorized routine work or
    reopen accepted decisions.
29. Follow the existing workflow: worktree for implementation; no `docs/`
    writes without permission; meaningful worklog; native, directly runnable
    tooling. No new document/ledger machinery is needed beyond this requested handoff.
30. **Put this initial project on `main` and keep the continuation simple.**
    The user explicitly requested this after discovering that the root checkout
    still looked empty. Do not leave the new session pointing at an empty main
    checkout or require it to find an old worktree to read the implementation.

## Current implementation choices (provisional, not all user requirements)

The PoC builds **unchanged [ysya/runscaler](https://github.com/ysya/runscaler)** at
`60ced08cbc3c6b52f728c87fbdbd225977ce9189`, using its Docker and Tart providers.
The installed executable is named `github-actions-runner`. This reuses an
existing manager built on GitHub's scale-set SDK; it is not a newly written
controller. It is also not yet established as a mature, production-qualified
dependency. Review it against the remaining claims before adopting it fleet-wide.

Earlier alternatives were researched: myoung34's Docker runner has the standard
systemd/ephemeral pattern; ARC would introduce Kubernetes; GitHub's Docker SDK
example calls itself demonstration-only. Tartelet's **current** documentation
supports personal repositories, despite an older org-oriented README. Its
GitHub App setup made it less convenient for this isolated PoC; do not repeat
the incorrect claim that personal repositories are categorically unsupported.

The old custom cross-platform controller proposal was withdrawn. The only new
native code is a small Swift **service-registration bridge**, not a runner
controller. It calls Apple's `SMAppService` to register/unregister an embedded
LaunchAgent. See `platforms/macos/ServiceRegistration.swift`.

### Bob: installed, tested, currently stopped

- SSH: `ssh -o BatchMode=yes bob`; Arch x86_64; user `tyler`; user-manager
  lingering is already enabled. No passwordless sudo.
- Owned PoC root: `/srv/github-actions-runner-poc/` with `bin`, `config`,
  `secrets`, `caches`, `logs`, `registry`, `images`, `artifacts`.
- User units: `github-actions-runner-poc.service`,
  `github-actions-runner-poc-registry.service`,
  `github-actions-runner-poc-cache-cleanup.service` and `.timer`.
- Scale-set label: `github-actions-runner-poc-bob`; private PoC repository only;
  minimum 0, maximum 1; 2 CPU, 4096 MiB RAM, 1024 pids; no host Docker socket in jobs.
- Image: `localhost:15000/github-actions-runner-poc:local`. The manager always
  pulls at startup, so a loopback-only registry serves the locally built image.
  Registry data lives under the PoC root. Latest observed image digest:
  `sha256:e9202e3aef21955822d15ef467bbab4a19aaa3383e48b846a1a66f804469f560`.
- Image source: `images/linux/Dockerfile`; official runner `2.338.1`, Go `1.27`,
  Node `24`, Vite+. Resolved during proof: Go 1.27.3, Node 24.22.1, vp 1.3.0,
  pnpm 12.15.0. Those observations are not new project patch pins.
- Three named Docker local-driver volumes bind to explicit host directories:
  `github-actions-runner-poc-go-mod` → `caches/go-mod` → `/cache/go-mod`;
  similarly `go-build` and `pnpm`. Mounted ownership must suit runner uid 1001.
- `PNPM_CONFIG_STORE_DIR=/cache/pnpm/store` and
  `PNPM_CONFIG_CACHE_DIR=/cache/pnpm/metadata` are necessary. Guessing `.npmrc`
  or `npm_config_store_dir` did not retain pnpm 12's resolution metadata;
  the offline second job exposed that failure.
- Weekly cleanup: Sunday 11:00 UTC (05:00 Costa Rica), randomized up to 30 min,
  persistent timer. systemd stops/drains the PoC manager, a networkless helper
  mounts only the three caches and empties their contents, then `OnSuccess` or
  `OnFailure` starts the manager. **This is a weekly full reset, not LRU or a hard
  quota.** Job drain timeout is 30 min; systemd stop timeout 1900 seconds.
- A manual native cleanup run succeeded: 58 MiB Go build, 208 KiB modules and
  127 MiB package data became empty; the manager restarted afterward.
- The generic disk guard is deliberately **off** on Bob. Inspection found it
  can reclaim global Docker stores under pressure even with their routine
  prune switches off. Do not enable it on this shared media daemon uncritically.
- Configured 2 GB/2 GB/1 GB cache budgets currently say `on-exceed="warn"`;
  with the guard off these are **not enforced**. Weekly retention does not close
  the instantaneous capacity-limit requirement.
- At handoff the two PoC services and cleanup timer are stopped and disabled.
  The cleanup oneshot is inactive. Original CI/media services were not migrated.

### macOS: image ready internally; real job proof still pending

- Host Apple Silicon; 24 GiB RAM, 10 CPUs. Latest measured internal free space
  after copying the image: about 43 GiB (refresh before making new large copies).
  Standard Time Machine thinning released already-purgeable local snapshots;
  no live project data was removed in this step.
- Internal data root: `/Users/tyler/CI/github-actions-runner/`.
  `tart/` owns images/clones/cache/temp state; `poc/config/` owns private config;
  `poc/logs/` owns manager diagnostics. Add caches/artifacts beneath this root
  when implemented; do not create alternate ad hoc homes.
- Official Tart 2.41.1: `/Users/tyler/Applications/Tart.app/Contents/MacOS/tart`.
  Archive checksum is recorded in `components.toml`.
- **All Tart operations must set**
  `TART_HOME=/Users/tyler/CI/github-actions-runner/tart`.
- Local golden VM: `github-actions-runner-poc-base`, stopped. Logical disk 50 GB,
  reported allocated size about 33 GB. Clones on the same APFS filesystem share
  unchanged blocks. The copy was SHA-256 verified against the provisioned source:
  `951cf675a330dbb89c0e991d57e2e61cc9842a3bca79c5aac9adb095713f4fb4` for `disk.img`.
- Base originated from `ghcr.io/cirruslabs/macos-tahoe-base:latest`, digest
  `sha256:4aaa751fa7538902d73c767f27a066fc87e83f183069da4e4b5022863abd4c77`.
  Guest macOS 26.6.2, admin uid 501, Apple clang 21, Node 24.22.0. Go was absent.
  Guest agent worked via `tart exec`; no SSH setup required.
- Guest runner directory `/Users/admin/actions-runner`, updated to `2.338.1` with
  checked archive SHA-256
  `52c3fb801b931fbd454979bae5ec3443ea3da2c4a1b4c44fa546fb630d61a0a9`.
  It is unregistered; do not bake a long-lived host credential into it.
- Installed app: `/Users/tyler/Applications/GitHub Actions Runner.app`;
  bundle ID `com.tylergannon.github-actions-runner`; signed with existing
  Developer ID Application: Tyler Gannon, team `6H59L2SRR6`.
  Deep/strict codesign verification passed. Local PoC is not notarized; no icon yet.
- Main executable `github-actions-runner-service` is the Swift registration
  bridge; actual manager `github-actions-runner` remains unchanged upstream code.
  Embedded agent: `Contents/Library/LaunchAgents/com.tylergannon.github-actions-runner.poc.plist`,
  using `BundleProgram` and real paths into the internal CI root.
- This new SMAppService registration **has not been run**. `status` currently
  reports “service not found”; no loaded PoC LaunchAgent is expected.
- The rejected legacy LaunchAgent is removed from `~/Library/LaunchAgents`;
  its disabled copy is in `~/CI/github-actions-runner/poc/config/`.
- Earlier legacy launch showed only `github-actions-runner` in System Settings
  and stalled in Tart filesystem enumeration against the external volume.
  The modern bridge and internal storage must now be tested; do not claim the
  new app is already properly attributed or that the exact stall cause is proven.
- Label: `github-actions-runner-poc-macos`; min 0, max 1; 4 vCPU, 4096 MiB;
  no warm pool. Tart image-cache pruning: every 6 h, max age 7 days, budget 8 GB.
  This prunes downloaded OCI/IPSW cache, **not** the golden local VM itself.
- Upstream Tart provider does **not** currently expose host shared-directory
  mounts. Mac shared Go/package caches remain an unmet design requirement.
- External copies remain at `/Volumes/Laptop Backups/GitHub Actions Runner/`
  solely as stopped, unused copies. No active configuration points there.
  Do not run from there. Remove only this task-owned directory later if desired;
  preserve all unrelated backups and volume contents.

## Proof already obtained, and what must not be claimed

At source revision `cb966c39eec6ea677af9d497f7948e3574189577`, two real jobs
passed in [run 39866659463](https://github.com/tylergannon/github-actions-runner/actions/runs/39866659463):

- [linux-populate](https://github.com/tylergannon/github-actions-runner/actions/runs/39866659463/job/120130434954),
  runner `runner-46d3dfb7`.
- [linux-reuse](https://github.com/tylergannon/github-actions-runner/actions/runs/39866659463/job/120130527736),
  different runner `runner-9879a856`: Go module lookup disabled (`GOPROXY=off`,
  `GOSUMDB=off`), literal UUID output correct, `vp install --offline` reused its
  dependency with zero downloads. All three cache markers persisted; the prior
  HOME marker did not. Worker containers were removed after jobs.

The overall workflow was **cancelled**, because macOS jobs had not run when
the user stopped external-drive work. Do not call that workflow green. The
later run `39869292924`, triggered by commit `5b6093e`, was also cancelled for
this handoff. Older exploratory runs `39865724471` and `39866178781` were cancelled
after initial Linux image/cache problems. No pending PoC workflow is intended.

The committed macOS workflow will compile a small C binary, ad-hoc sign and
verify it, then check fresh HOME state in a second VM. **It has not run yet.**
Even once it passes, it does not prove Developer ID release signing or full
skgo/Gimbal application qualification. The host app signature is a different claim.

Remaining material gaps before production adoption:

- Real GitHub jobs in two successive Mac clones, distinct runner identity,
  fresh HOME, compilation/signing check and clone deletion.
- Actual System Settings attribution with the modern native app registration;
  enable/disable/stop/start behavior, restart/update and reboot behavior.
- Failure, cancellation, interruption and crash cleanup on both platforms;
  scoped child-container/workspace cleanup for existing Docker-using qualification.
- Mac cache sharing; signing credential delivery to guests; actual release jobs.
- Enforced capacity protection and per-category budgets. Current guard behavior
  logs reclaim failures and can still admit work; do not claim fail-closed admission.
- Full artifact/export retention and bounded logs. Upstream rotates its manager
  log; current macOS stdout/stderr files can grow independently and need a policy.
- Production fleet migration, common application tool declarations, old cache
  reclamation and measurement-based worker counts.

## Continuing from the new session

Start in the repository directory on `main`, read this file plus `CURRENT.md`, and
verify state before starting anything. `DESIGN.md` and the old README contain
earlier proposals; this handoff records the later user corrections and PoC facts.

```sh
cd /Users/tyler/src/github-actions-runner
git status --short
just --list
just storage-macos
just vms-macos
```

Finish macOS execution/native identity first, without rebuilding the already
downloaded image or returning to external storage. The app is installed but
unregistered. `just start-macos` calls its native `register` command;
`just stop-macos` unregisters it; `just status-macos` inspects both native
registration and launchd. Inspect real System Settings behavior afterward.
If macOS requires a user action, explain the exact prompt and ask a pointed question.

For Bob, `just start-bob` starts the registry dependency and manager;
`just status-bob` / `just caches-bob` inspect them. `just clean-caches-bob`
drains the PoC service, clears exactly its caches and starts it again. For
automatic operation later, deliberately re-enable the two services and
`github-actions-runner-poc-cache-cleanup.timer`; they are disabled at handoff.

The workflow is `.github/workflows/poc.yml`. It runs on PR changes to that
workflow, `hosts/**`, `images/linux/**` and `examples/cache-demo/**`.
The workflow is now available on default `main`, so it can be dispatched directly:

```sh
gh workflow run poc.yml --repo tylergannon/github-actions-runner --ref main
gh run list --repo tylergannon/github-actions-runner --limit 5
# Watch the new run ID with gh run watch --exit-status.
```

The earlier run IDs remain historical proof, not proof of the current main SHA.
If implementation changes, test the new SHA. Merging this initial PoC at the
user's request does not establish production readiness or close the gaps above.

Build/repackage recipes are in `justfile`: `build-manager` builds unchanged
upstream source for darwin/arm64 and linux/amd64; `build-macos-app IDENTITY`
compiles the small Apple bridge, stages metadata/agent/license and signs the
app. Generated source downloads/build outputs are ignored under
`ephemeral/reference/`, `ephemeral/downloads/`, `ephemeral/private/`, `build/`.
The meaningful tracked worklog is `ephemeral/worklog/native-runner-design.md`.

### Credentials and boundaries

No credential values belong in Git, this handoff, terminal output or the VM
base. Existing local `gh` authentication supplied the host manager credential.
Linux: `/srv/github-actions-runner-poc/secrets/service.env`, mode 600.
macOS: `/Users/tyler/CI/github-actions-runner/poc/config/runner.private.toml`,
mode 600. Do not print either. Source TOML uses `env:RUNNER_TOKEN` placeholders;
the private Mac config currently contains the token value. Only per-job JIT
configuration should enter a disposable worker.

## Existing fleet and completed cleanup

`CURRENT.md` is the separate dated inventory with source paths, service labels,
disk measurements and evidence. It is not a blanket safe-deletion list.

- Mac: two skgo runners plus one Gimbal runner under the old home directories.
- Bob: eleven container workers across skgo, Gimbal and skgo-project, plus the
  native private core-qualification runner and ARM64 emulation prerequisite.
- The native qualification tree was about 57 GiB, mainly 26 retained attempts.
  Retained per-attempt agent homes alone were 40.76 GiB, including repeated
  browsers, Go and package caches. skgo/Gimbal shared cache trees were about
  41 GiB and 15 GiB. Three older container writable layers were another ~94 GB
  decimal. Do not double-count nested categories or APFS shared blocks.
- The user separately authorized old internal media-staging cleanup on Bob.
  Exactly 13.4 GiB of obsolete restore-test/duplicate ZIP/partial TAR data and
  one stopped migration-check container were removed after verification against
  preserved complete backups. Live `/srv/media`, configs and complete backups
  were kept; Jellyfin/Transmission stayed healthy. This cleanup is already done.
- `github-worker.service` is an unrelated issue-dispatch worker, not an Actions
  runner. Do not include it in runner replacement solely because of its name.

Do not redo completed media cleanup, assume every old runner is redundant,
or let the PoC's temporary choices become unexamined production requirements.
