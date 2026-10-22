# GitHub Actions Runner infrastructure

One home for our runner configuration on Amritanandamayi (macOS) and Bob
(Linux): recognizable native OS services, established runner implementations,
and explicit, bounded storage.

**Status: design proposal.** Existing runners have not been migrated.

The proposed Linux baseline is an existing Docker runner's documented
systemd/ephemeral-container setup. The accepted macOS approach is one disposable
VM per job; evaluate existing VM runner managers before writing native
lifecycle code. This repository defines our installation
and storage policy; a custom cross-platform runner supervisor is not planned.

One CI storage root contains job workspaces, a few useful cache mounts
(initially Go modules, Go build output and the package store), and deliberately
retained artifacts. Worker images share installed tool layers. Node is requested
as `24`; patch releases are normal maintenance.

- [Design, reuse assessment and storage requirements](DESIGN.md)
- [Observed installations and disk usage](CURRENT.md)

Acceptance includes real jobs, native OS identity/lifecycle and demonstrated
storage reuse, cleanup and budgets.
