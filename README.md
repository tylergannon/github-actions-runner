# GitHub Actions Runner infrastructure

One repository owns the runner definitions, native services and storage policy
for Amritanandamayi (macOS) and Bob (Linux).

The isolated PoC has passed real GitHub jobs on both hosts: disposable Linux
containers reuse three declared caches, and successive disposable macOS VMs
compile/sign/run a binary with fresh HOME state. The signed Mac application
appears as **GitHub Actions Runner** in System Settings. Production runners
have not been migrated; storage enforcement and release qualification remain.

- [Operate, reproduce proof, inspect evidence and see remaining gaps](OPERATIONS.md)
- [Accepted requirements and component choices](DESIGN.md)
- [Dated inventory of the existing fleet](CURRENT.md)

The PoC packages unchanged runscaler with Docker/Tart providers, systemd on Bob
and a small Apple ServiceManagement registration bridge on Mac. Runtime data
lives under `/srv/github-actions-runner-poc/` and internal
`~/CI/github-actions-runner/`. Installed services do not depend on this checkout.
Node is requested as `24`; frontend commands use Vite+.
