# GitHub Actions Runner infrastructure

A centralized place to run our GitHub Actions jobs on self-hosted Linux and
macOS machines. Runners stay ready between jobs, with the software they need
already installed. Running a task should not require setting up the machine
or reinstalling its tools every time.

This README defines the intended behavior and repository scope. The current
implementation still needs to be brought into alignment with it.

## Required behavior

- **Persistent runners and software.** Keep runners, toolchains and required
  shared software installed across jobs, restarts and weekly cleanup. Software
  installation and updates are deliberate maintenance operations.
- **Known execution locations.** Route our GitHub Actions jobs to an explicitly
  configured runner pool. Runner names and labels should make it clear in GitHub
  which machine runs each job.
- **Proper operating-system identity.** Installed services and macOS background
  items must be identified as **GitHub Actions Runner**, with recognizable names
  for individual runners. An incidental script or interpreter name is not an
  acceptable background-item identity.
- **Bounded capacity.** Configure runner counts and concurrency explicitly so
  the service cannot grow unchecked or take over the host. Preserve the capacity
  needed by existing jobs when replacing runners.
- **One obvious CI data location per host.** Keep runner configuration, state,
  software and accumulating job data under a declared CI root, with permanent
  installations separated from cleanup targets. Native app bundles and service
  registrations use their normal OS locations and are documented.
- **Regular, scoped cleanup.** Weekly maintenance removes accumulated caches,
  old build output, temporary files and expired artifacts/logs. It preserves
  installed software, runner registration and configuration, and avoids active
  jobs and unrelated host data.

Clearing a cache may require the next job to refill it. It must not uninstall
the tools needed to run that job. Per-job disposable containers or VMs are not
a requirement.

## What this repository should contain

- Service installation and management for Linux and macOS, including correct
  naming, automatic startup, status, stop and removal.
- Repeatable provisioning and update instructions or scripts for the software
  required by our jobs.
- Runner configuration covering repository access, routing, names, capacity
  and data locations.
- A documented storage layout and cleanup rules that distinguish permanent
  installations from accumulating data.
- Operating instructions and checks that demonstrate real jobs work and the
  installation remains usable after cleanup.

Application repositories continue to own their workflows, build commands and
tests. Credentials, private host configuration and execution evidence stay
outside this public source repository.

## Current implementation and gaps

The existing proof of concept uses [runscaler](https://github.com/ysya/runscaler)
to create disposable Linux Docker workers and macOS Tart VMs. It includes native
service packaging, a Linux toolchain image, example configurations and a
qualification workflow.

That lifecycle does not yet meet the persistent-runner requirement. The Linux
example preserves three shared caches but deletes their contents weekly; shared
macOS caches are a documented gap. Existing design and operating documents
describe that proof of concept and must be reconciled with the requirements
above as implementation changes.

- [Existing design and component choices](DESIGN.md)
- [Existing build and operating instructions](OPERATIONS.md)
- [Linux image](images/linux/Dockerfile) and [native service packaging](platforms/)
- Configuration examples: [Linux](examples/linux.toml), [macOS](examples/macos.toml),
  [multiple Linux projects](examples/linux-fleet.toml),
  [multiple macOS projects](examples/macos-fleet.toml)
- [Existing qualification workflow](examples/workflows/poc.yml)

## Acceptance

Run a real project workflow twice, perform the regular cleanup, then run it
again. Required software and runner registration must survive, jobs must reuse
the installed tools, and eligible accumulated data must be removed. Verify
recognizable identities in GitHub and OS service/background-item settings,
declared storage locations and bounded runner capacity.
