# GitHub Actions Runner infrastructure

Native service packaging and example configuration for disposable GitHub Actions
workers: Docker containers on Linux and Tart macOS VMs on Apple hardware.

The proof of concept reuses an unchanged [runscaler](https://github.com/ysya/runscaler)
manager. systemd owns the Linux service; a small Swift SMAppService bridge
registers the macOS app as **GitHub Actions Runner**. Each job gets a disposable
workspace and HOME. Linux workers share three explicit Go/package caches.

- [Requirements and component choices](DESIGN.md)
- [Building, configuring and operating](OPERATIONS.md)
- [Linux configuration example](examples/linux.toml)
- [macOS configuration example](examples/macos.toml)
- [Manual qualification workflow](examples/workflows/poc.yml)

The delivery target is a working replacement for an existing project's jobs:
real workflows pass, installed services start automatically, completed workers
are removed, and weekly maintenance handles routine storage care. Node is
requested as `24`; frontend commands use Vite+.

This public infrastructure repository does not run self-hosted Actions. Qualify
consuming projects using trusted branches or controlled manual dispatches; route
fork PR checks to GitHub-hosted workers and retain approval for external workflows.
Host-specific
configuration, credentials, inventories and execution evidence belong outside
this public source repository.
