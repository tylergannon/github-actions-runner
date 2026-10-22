# Inspected runner installations

Observed read-only on **2026-10-22**, using local launchd/process/configuration
inspection and SSH to Bob. This is a dated inventory, not a complete history
of who created every installation. No credentials are included. Counts refer
to installed/running instances, not a guarantee of GitHub connectivity.

## Amritanandamayi: macOS

Three running per-user launch agents:

| GitHub repository | Registration name | Installation |
| --- | --- | --- |
| tylergannon/skgo | amritanandamayi-skgo | `/Users/tyler/actions-runner-skgo` |
| tylergannon/skgo | amritanandamayi-skgo-2 | `/Users/tyler/actions-runner-skgo-2` |
| tylergannon/gimbal | amritanandamayi | `/Users/tyler/actions-runner-gimbal` |

The two skgo plists under `~/Library/LaunchAgents/` point directly at
`runsvc.sh`. Gimbal's plist points at `~/.local/bin/start-gimbal-actions-runner`,
which invokes its installation's `runsvc.sh`.

The service labels are:

```text
actions.runner.tylergannon-skgo.amritanandamayi-skgo
actions.runner.tylergannon-skgo.amritanandamayi-skgo-2
actions.runner.tylergannon-gimbal.amritanandamayi
```

skgo's source definition is `scripts/ci/deploy-macos-runners.sh`, introduced
by commit `277d3bc640f67c059daca09677a4b6c00d488fcf` / PR #434. It explicitly
creates two installations under `$HOME`; both use the same job labels.

The installations reported approximately 1.1 GiB, 984 MiB and 2.3 GiB through
`du -h`. Each runner package contributes about 439 MiB, including about
353 MiB of bundled Node 20/24 runtimes. Both skgo workers also retain a
271 MiB Go tool installation. Gimbal retains two Go versions, another build
Node installation and GoReleaser in its 910 MiB tool cache; its CI checkout
is about 891 MiB, including frontend dependencies and release output.
These filesystem usage figures are not guaranteed physical reclamation
figures on APFS.

The workflows disagree in Node selection: skgo requests `24.22.0`, while
Gimbal requests `24`. The agreed design policy is `24`.

## Bob: Arch Linux and systemd

SSH alias `bob` resolves to host `bob`, running Arch Linux and systemd 260.
The inspected user is `tyler`; `loginctl show-user tyler` reports
`Linger=yes`. Docker is a system service. The runner containers themselves
currently use Docker's `unless-stopped` policy rather than individual systemd
service definitions.

Eleven running runner containers were observed:

| Repository | Containers | GitHub registration names | Installed definition |
| --- | --- | --- | --- |
| tylergannon/skgo | `skgo-release-runner-1` through `-4` | `bob-skgo-release-1` through `-4` | `~/.local/share/skgo-release/scripts/ci/bob-runners.compose.yml` |
| tylergannon/skgo | `skgo-release-runner-arm64` | `bob-skgo-release-arm64` | Same Compose file, ARM64 profile |
| tylergannon/gimbal | `gimbal-actions-runner-1`, `-2` | `bob-gimbal-1`, `-2` | `~/.local/share/gimbal-release/compose.yml` |
| tylergannon/skgo-project | `skgo-actions-runner`, `-2`, `-3`, `-blind` | `bob-skgo`, `bob-skgo-2`, `bob-skgo-3`, `bob-skgo-blind` | No Compose provenance label found |

The skgo Compose source, images and deployment procedure live in skgo's
`scripts/ci/`. Gimbal's Dockerfile and Compose source live in Gimbal's
`scripts/ci/`. Its deployed directory contains both a `Dockerfile` and
`bob-runner.Dockerfile`; this inventory has not established every file's
relationship to the deployed image.

The skgo workers have 4 CPU / 8 GiB container limits; Gimbal workers have
8 CPU / 16 GiB limits. The older skgo-project containers have 3 CPU / 10 GiB
limits. These are limits, not measured utilization or capacity justification.

skgo shares several cache mounts under `~/.cache/skgo-release/`, while
Gimbal uses `~/.cache/gimbal-actions/`. Both bind mount
`/home/tyler/go/pkg/mod`. Gimbal also shares a tool-cache mount between its
two workers. Job workspaces are separate. The four older skgo-project
containers inspected have no mounts; important state can therefore reside in
their writable layers. Do not remove/recreate them on an assumption that
their registration or work data already lives in a durable host mount.

There is also a running **native** runner, separate from those eleven
containers:

```text
Unit:         skgo-core-qualification-runner.service (systemd user service)
Description:  SKGO private core qualification runner
Definition:   ~/.config/systemd/user/skgo-core-qualification-runner.service
ExecStart:    ~/.local/share/skgo-project-core-runner/run.sh
Repository:   tylergannon/skgo-project
Registration: bob-skgo-core-qualification
```

`skgo-project/.github/workflows/qualify.yml` selects the
`skgo-core-qualification` label. Its private qualification role is a distinct
consumer that must be accounted for in migration.

A second runner-related unit is
`~/.config/systemd/user/bob-arm64-emulation.service`, description
`ARM64 execution for skgo's release runner on Bob`. It is an enabled oneshot
that registers ARM64 binfmt handlers through a privileged container. The
ARM64 skgo runner executes under emulation on the x86_64 host.

`github-worker.service` is a failed, separate issue-label dispatch worker
for Codex/Claude via River. Its name does not make it a GitHub Actions runner;
it is outside this migration scope.

`du -sh` also reported the following existing host trees:

| Directory | Reported usage |
| --- | ---: |
| `~/.local/share/skgo-project-core-runner` | 57 GiB |
| `~/.cache/skgo-release` | 41 GiB |
| `~/.cache/gimbal-actions` | 15 GiB |

These are aggregate directory figures, not an itemized explanation or a safe
deletion list. They exclude other potentially relevant storage, including
Docker image/layer storage and the shared Go module directory. Cleanup needs
an ownership and retention decision before removal.

### Follow-up disk breakdown

Read-only follow-up on the same day found:

- Of the 57 GiB qualification runner tree, about 55 GiB is
  `.local/qualification/` in the evaluator checkout. There are 26 attempt
  directories: 22 have state `completed`, one `failed`, and three have no
  readable `attempt.json`.
- Agent delivery directories total 41.38 GiB, almost entirely retained agent
  homes (40.76 GiB). Across those homes, Playwright browser caches total
  15.28 GiB, Go build caches 11.11 GiB, package-manager caches 7.22 GiB,
  `go/` trees 3.79 GiB, and `.local/` trees 3.30 GiB. These categories include
  nested paths and must not be added to their parent totals again.
- Other attempt subdirectories total 6.03 GiB of frozen applications,
  4.47 GiB of assessment Go caches, 1.04 GiB of prepared tools, 0.77 GiB of
  source checkouts and 0.55 GiB of output. This is an aggregation of named
  subdirectories, not an exhaustive accounting of top-level files.
- The qualification workflow uses `actions/checkout` with `clean: false`.
  Its run script gives each attempt an agent home under `delivery/.home`.
  Cleanup removes attempt containers and authentication but retains the
  attempt directory. A frozen source archive excludes application build
  dependencies; this does not remove the original agent home and its caches.
- skgo's shared Go build cache is about 37 GiB of its 41 GiB tree. Gimbal's
  shared Go build cache is about 6.6 GiB of its 15 GiB tree. Gimbal also has
  2.3 GiB of Lightpanda-related tools/cache, about 1.35 GiB across two runner
  update staging directories, frontend tooling, and browser caches.
- Outside those three host trees, Docker reports roughly 29.7 GB, 31.1 GB
  and 33.2 GB in the writable layers of the three older skgo-project workers.
  Sampling the largest found about 13 GiB of Go build cache, 8 GiB in `/tmp`,
  plus Go modules, frontend tooling and browsers. Docker's decimal layer
  sizes and `du`'s binary directory sizes are different measurements.

The qualification job owns deciding which evidence to retain after an
attempt. Runner infrastructure owns shared cache budgets and workspace
lifecycle. Moving unit files alone addresses neither accumulation source.

## Inspection boundaries

The GitHub API confirmed the three Mac registrations online and idle earlier
in this conversation. Bob container `.runner` files establish configured
repository ownership; they alone do not prove current online status or
recent job consumption. Live GitHub registration and job history must be
checked at migration time.

Current macOS background-item attribution has not been demonstrated through
System Settings during this inspection. The proposed app/ServiceManagement
packaging must earn that claim through native acceptance, not metadata alone.
