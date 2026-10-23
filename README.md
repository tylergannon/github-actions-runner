# GitHub Actions Runner infrastructure

A centralized place to run our GitHub Actions jobs on Linux and macOS, with
required software already installed, recognizable services and predictable
storage cleanup.

Agents: read [llms.txt](llms.txt) to use a project-owned image and preserve the
weekly cleanup contract.

[runscaler](https://github.com/ysya/runscaler) starts ordinary job containers or
Mac VMs on demand, within explicit capacity limits, and removes them afterward.
With no jobs, there are no ordinary workers running. Installed software stays in
reusable container images and Mac base VMs. Starting a worker must not mean
reinstalling its toolchain. Native release and private qualification runners
remain in the same inventory where their workloads require persistent execution.

## Required behavior

- **Persistent software, on-demand workers.** Keep prepared environments and
  required tools across jobs, restarts and weekly cleanup. Ordinary workers
  scale to zero; the manager stays available to receive jobs.
- **Current tools.** Use current stable releases. Go 1.27.3 is the current
  migration baseline. Refresh prepared environments during maintenance, rather
  than downloading toolchains in every task. Account for consuming workflows
  that still request an older version before retiring that installation.
- **Known execution locations.** Runner names and routing labels identify the
  host and workload. One fleet inventory covers every managed runner.
- **Proper OS identity.** Services and macOS background items belong to
  **GitHub Actions Runner**, not an incidental script or interpreter.
- **Bounded capacity.** Explicit runner counts, concurrency and resource limits
  prevent unchecked expansion. Preserve the capacity existing jobs need.
- **One CI data root per host.** Separate installed tools, configuration and
  prepared environments from accumulating job data. Native app bundles and
  service registrations use their documented OS locations. Account for
  container-engine storage separately from bind-mounted CI data.
- **Scoped weekly cleanup.** Remove accumulated caches, build output, temporary
  files and expired logs/artifacts. Preserve tools, prepared environments,
  registration, configuration and retained private evidence. Avoid active jobs
  and unrelated host data.

Clearing dependency caches can require a later job to refill them. It must not
uninstall the software needed to run that job. Tool caches such as GitHub's
`_work/_tool` contain installed software and are not weekly cleanup targets.

## What belongs in this repository

- [Native services and the named Mac app](platforms/), with startup, status,
  stop and removal support.
- [Linux worker image](images/linux/Dockerfile) and repeatable tool provisioning
  for Linux, Mac bases and native runners.
- Runner configuration for access, routing, capacity and storage:
  [Linux](examples/linux.toml), [macOS](examples/macos.toml),
  [Linux fleet](examples/linux-fleet.toml), [Mac fleet](examples/macos-fleet.toml).
- [Fleet](examples/fleet.json) and [host](examples/host.json) manifests, and
  [one operator command](scripts/fleet.py) for status and weekly maintenance.
- [Operating instructions](OPERATIONS.md), [design constraints](DESIGN.md) and
  [qualification workflow](examples/workflows/poc.yml).

Application repositories own their workflows, build commands and tests.
Credentials, machine-specific manifests and execution evidence stay outside
this public repository. External fork jobs retain their existing GitHub-hosted
routing and approval boundaries.

## Updating a project’s software

Projects own their Dockerfiles and published runner images in their own
repositories. They may extend the shared Linux image or provide a compatible
runner image, with required tools installed at image-build time. A Dockerfile
under `images/PROJECT/` here is optional. Set that
project’s `[[scaleset]]` `runner-image` to the tag; macOS scale sets can likewise
select their own prepared Tart base VM. Drain existing jobs before restarting
the manager with changed configuration.

The existing manager already supports a different image per project. Image
updates do not require changing application code or making every project’s
tests pass. Keep installed tools out of cleanup targets. See
[the configuration example](examples/linux-fleet.toml) and
[build instructions](OPERATIONS.md#project-specific-images).

## Storage and operation

| Keep installed | Eligible for cleanup |
| --- | --- |
| Manager and native runner installations | Completed-job workspaces and temporary files |
| Toolchains and tool caches | Dependency downloads and rebuildable build caches |
| Current worker images and Mac base VMs | Superseded images under an explicit retention policy |
| Configuration, registration and credentials | Expired logs and artifacts |
| Retained private reports and journals | Explicitly declared disposable data |

Use the installed operator with the private fleet manifest:

```sh
python3 CI_ROOT/bin/fleet.py CI_ROOT/config/fleet.json status
python3 CI_ROOT/bin/fleet.py CI_ROOT/config/fleet.json maintain
```

The scheduled maintenance task covers every declared host. systemd and the
signed Mac app own services; runscaler owns ordinary worker lifecycle. Native
exceptions remain declared and visible. Docker's engine and supporting services
can remain running when ordinary worker count is zero.

## Acceptance

Run real workflows twice, perform weekly cleanup, then run them again. Verify
that required tools are reused without reinstallation, eligible accumulated
data is removed, retained data survives and ordinary workers return to zero.
Check identities in GitHub and OS background settings, declared storage paths
and capacity limits. Measure idle manager resource use separately from Docker
and other supporting services. Passing an example alone does not establish
that every consuming workflow has been migrated.
