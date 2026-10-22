# GitHub Actions Runner

One home for the GitHub Actions runner infrastructure on Amritanandamayi
(macOS) and Bob (Linux).

The operating system must identify and control it as **GitHub Actions
Runner**. A compiled `github-actions-runner` executable and native service
definitions provide that identity. Projects own their build commands; this
repository owns runner installation, host definitions, lifecycle and shared
build tools.

**Status: design proposal.** No service implementation or migration has been
installed. Existing runners continue unchanged.

- [Service and installation design](DESIGN.md)
- [Observed installations and their current owners](CURRENT.md)

Node policy is `24`, shared across projects. Patch releases are routine tool
maintenance, not edits to every application's workflow.

Deployment is complete only when the installed service is recognizable in
macOS System Settings or systemd, receives a real GitHub job, and responds
correctly to the operating system's lifecycle controls.
