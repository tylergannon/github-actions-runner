# Runner infrastructure: standard components, owned storage

**Design proposal, revised 2026-10-22.** Existing runners remain unchanged
pending alignment and a measured migration. [CURRENT.md](CURRENT.md) is the
separate factual inventory.

## Desired state

This repository defines how our GitHub Actions runners are installed, named,
started and stopped on macOS and Bob. It also defines exactly where CI writes
and who cleans it up. An operator can identify the owning repository and find
its workspaces, caches, artifacts and logs without searching application
repositories or arbitrary home directories.

Use established runner implementations and native OS units. The earlier
proposal to build a new cross-platform service adapter is withdrawn. A new
repository for configuration does not require a new runner product.

## Existing implementations and the proposed choice

| Component | Established implementation | Fit here |
| --- | --- | --- |
| Single-host Linux workers | [myoung34/docker-github-actions-runner](https://github.com/myoung34/docker-github-actions-runner/wiki/Usage#systemd) | Recommended starting point for Bob; documents the exact systemd plus ephemeral Docker pattern |
| Kubernetes fleet | [GitHub Actions Runner Controller](https://docs.github.com/en/actions/concepts/runners/actions-runner-controller) | Established full controller; no reason yet to add a Kubernetes cluster for this host |
| Scale-set SDK | [actions/scaleset](https://github.com/actions/scaleset) | Building block for custom controllers; its Docker example expressly says it is not production-ready, so it is not a turnkey answer |
| Disposable macOS environments | [Tart](https://github.com/openai/tart) with an existing runner manager such as [Tartelet](https://github.com/framna-dk/tartelet) | Evaluate before writing a macOS manager; repository scope, signing, host compatibility and OS-visible identity need qualification |
| Mac runner without a VM | [GitHub's runner service](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application) | Supported fallback for macOS-only jobs; still needs deliberate storage ownership and recognizable native attribution |

This is a researched recommendation, not a claim that any replacement has
been installed or qualified. Tartelet's documented flow uses organization
registrations, whereas our inspected repositories are personal-account
repositories. Do not assume that it fits without verifying that boundary.

GitHub's own documentation supports ephemeral runners that receive one job.
Deregistering a runner alone does not remove a persistent mounted workspace.
The OS unit and storage lifecycle must dispose of the owned execution data.

## One storage root, several straightforward cache mounts

All host-visible job data and caches live beneath one declared CI storage
root. For Bob, propose `/srv/github-actions-runner`, provisioned on a
size-controlled filesystem or subvolume. This path is a proposal, not an
existing mount. Do not make a subdirectory per incidental HOME or tool
installer outside this root.

```text
/srv/github-actions-runner/
  config/                   installed non-secret instance definitions
  secrets/                  restricted registration credentials
  jobs/<instance>/<job>/    independent workspaces and temporary agent homes
  caches/
    go-mod/                 shared Go module downloads
    go-build/               shared compiled Go objects
    pnpm/                   package store used by Vite+
  artifacts/<job>/          explicitly exported results and diagnostics
```

These are separate bind mounts from one parent tree, not a collection of
unrelated host directories. Start with the three caches above. Add another
only for a concrete performance benefit and document its destination and
cleanup owner. A browser or tool download does not automatically earn its own
permanent host mount.

| Mount | Container configuration | Lifetime |
| --- | --- | --- |
| `caches/go-mod` | `GOMODCACHE=/cache/go-mod` | Reusable downloads; bounded independently of jobs |
| `caches/go-build` | `GOCACHE=/cache/go-build` | Reusable compiler output; may be rebuilt after eviction |
| `caches/pnpm` | Configure the actual package store used by `vp install` | Reusable packages; confirm the effective path rather than mounting several guessed locations |
| `jobs/...` | Workspace, HOME and temporary directories for one job | Removed after deliberate artifact export and job termination |
| `artifacts/...` | Explicit publication/retention destination | Kept under a stated retention policy |

Dependency installations such as project `node_modules` belong to the job's
workspace. Share download stores rather than making different jobs mutate the
same application dependency directory. Share caches among compatible jobs;
keep private qualification state and credentials isolated from application
jobs. Use the cache's own compatibility keys; split storage only when a real
compatibility or ownership constraint requires it.

Docker-managed images, layers and build cache also consume disk. They are an
explicitly accounted storage category, never invisible overhead. Bob currently
shares its Docker daemon with media services. Do not move its global data root
or globally prune it as part of runner setup. Record that engine-owned store
alongside the CI bind-mount root; use scoped image/build-cache ownership and
budgets. A dedicated engine/storage domain can be a later decision if strict
physical containment requires it.

On macOS, use one declared CI data root too. Native application bundles,
ServiceManagement registration and OS-managed logs remain in their standard
OS locations. Those are named installation metadata, not permission for jobs
to create random host HOME trees.

## Bob: systemd starts standard container workers

Use the documented upstream pattern: a native systemd unit executes
`docker run --rm` in the foreground, with `EPHEMERAL=1`. The runner accepts
one job, exits, and systemd starts a fresh container. Docker's independent
restart policy is disabled. `systemctl stop` keeps the service stopped.

Use a recognizable template such as `github-actions-runner@.service`, with
instance descriptions identifying the repository and slot. The unit directly
executes `/usr/bin/docker`; it does not invoke a new Go supervisor or a homegrown
shell restart loop. Journald captures the service's output. Instance metadata
links its OS unit, container, GitHub registration, source revision and paths.

Bob's existing user manager has `Linger=yes`, so user units are a legitimate
boot-start option without requiring interactive login. System units with an
explicit execution account are also valid. Choose one installation scope
before implementation; changing accounts requires a deliberate cache and
credential ownership migration. Do not silently change scope during install.

The upstream no-workspace-mount example is the simplest disposable case.
Our qualification jobs also start child containers that bind-mount workspace
files, so their paths must resolve consistently for the host Docker daemon.
Use an explicitly owned workspace beneath `jobs/`, mounted at the same path
where needed. Its persistence is bounded by the job lifecycle; an ephemeral
runner registration does not clean a bind mount by itself.

A stop must terminate and wait for the owned container and its child jobs.
Killing an attached Docker client alone is insufficient. Startup after a
crash/reboot reconciles only this service's abandoned containers and inactive
job directories. It does not sweep another repository's work or the media
services. No sentinel-file wait loops.

Keep the current Ubuntu environment initially because Bob is Arch. Apply CPU
and memory limits to the actual containers. ARM64 remains an explicitly
emulated execution profile, with its named binfmt prerequisite owned here.
Preserve workflow labels and existing repository scopes during migration.

## macOS: macOS jobs require a macOS execution environment

Docker Desktop on a Mac runs Linux containers. It does not provide macOS,
Xcode, Apple's signing tools or Darwin runtime tests. Those jobs must run on
macOS, directly or inside a macOS VM. Linux jobs belong on Bob.

Evaluate existing Tart-based VM managers first. A disposable VM can provide
the same fresh-environment property as a disposable Linux container. Its base
images, clones and caches need a visible storage root and budget too; moving
unbounded state into VM images does not satisfy the storage requirement.

The native host application/service must identify itself meaningfully in
System Settings, have consistent application metadata/signing, and respect
OS enable/disable controls. Inspect the installed entry and its information
panel. Do not treat a friendly plist Label as proof of correct attribution.
If an existing manager meets these requirements, retain its legitimate app
identity and document its purpose. Only a demonstrated attribution gap would
justify a minimal native packaging bridge around the supported runner.

The exact macOS manager remains an open selection. Verify personal-repository
routing, the current host OS, real signing jobs, startup, stop, cleanup and
update behavior before adopting one. Do not build a custom macOS controller
while that reuse evaluation is unfinished.

## Bounded storage is an acceptance requirement

Every persistent path has an owner, a purpose, a budget and a removal rule.
The first implementation must propose concrete budgets against measured job
needs; an unspecified quota or a promise to occasionally prune is incomplete.

- Workspace and agent HOME: dispose after exporting results. Failed-job debug
  retention is explicit and bounded; cancellation/crash recovery handles
  leftovers after confirming no job still owns them.
- Go/package caches: reuse across jobs, report their size, and evict under a
  declared budget while writers are stopped. Never clean an active cache
  arbitrarily or assume Go's age-based trimming is a disk quota.
- Artifacts: keep reports, source/digests and requested diagnostics according
  to policy. Keeping evidence does not mean retaining every browser download,
  package cache, tool binary and scratch home for every attempt.
- Logs: bounded journald/file retention, with ephemeral runner diagnostics
  exported before disposal.
- Images and Docker build cache: scoped retention and BuildKit GC policy.
  No host-wide Docker pruning on the shared media/CI machine.
- Capacity: report usage by category and stop admitting work before exceeding
  the CI storage budget. Never treat free space on unrelated media storage as
  the runner's unlimited overflow area.

Use standard filesystem quotas/subvolume limits, existing cache/GC tools and
native scheduled cleanup units where appropriate. The repository stores the
configuration and policies; there is no new storage-management platform.
A bind mount makes data ownership legible, but does not itself enforce a quota.

## Tools

Node is requested as **`24`** across the fleet. Patch upgrades are normal
image/tool maintenance, not edits to every project's workflow. Keep Vite+ as
the frontend command surface. Avoid overlapping installers for the same tool.

Preinstalled compilers and build Node can live in the worker image: Docker
shares image layers among workers. On native hosts, reuse the existing shared
tool manager. GitHub's bundled Node is part of its runner distribution and
remains intact. Record resolved tool versions for jobs without turning those
observations into automatic patch pins.

## Repository responsibility and acceptance

This repository owns OS units, host/slot configuration, approved worker/base
images, explicit mounts, cache budgets, retention configuration and migration.
Application repositories own their workflow/build commands and which outputs
constitute useful evidence. The qualification harness must export that evidence
and stop treating its entire agent home as a permanent report.

Keep skgo, Gimbal and skgo-project as separate repository scopes. Determine
live consumers before retiring workers. Worker counts remain an explicit
capacity decision, not an installation side effect.

Prove one Linux slot and one macOS slot before migration. Acceptance requires:

- Recognizable installed OS identity and working native start/stop/disable,
  startup and restart controls.
- A real GitHub job routed through the intended labels and repository scope.
- Two successive jobs reuse the declared cache directories while their
  workspace/HOME data has the specified independent lifecycle.
- Successful, failed, cancelled and interrupted jobs leave no unaccounted
  writable directories or child containers.
- Storage reports locate every CI write in a declared mount, container/VM
  storage domain or OS-managed log location, with enforced budgets and
  retention. No new scattering across host home directories.
- Existing media services and private qualification boundaries remain intact.

## Source references

- [Docker runner: native systemd example and ephemeral lifecycle](https://github.com/myoung34/docker-github-actions-runner/wiki/Usage#systemd)
- [GitHub: ephemeral runners and external log retention](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
- [GitHub: ARC](https://docs.github.com/en/actions/concepts/runners/actions-runner-controller)
- [GitHub: Docker scale-set example, expressly demonstration-only](https://github.com/actions/scaleset/tree/main/examples/dockerscaleset)
- [Docker: one restart authority](https://docs.docker.com/engine/containers/start-containers-automatically/)
- [Docker Desktop for Mac: Linux VM and image storage](https://docs.docker.com/desktop/troubleshoot-and-support/faqs/macfaqs/)
- [Tartelet: disposable macOS runner VMs](https://github.com/framna-dk/tartelet)
- [Apple: native ServiceManagement registration](https://developer.apple.com/documentation/servicemanagement/smappservice)
