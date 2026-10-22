# GitHub Actions Runner infrastructure

One home for our runner configuration on Amritanandamayi (macOS) and Bob
(Linux): recognizable native OS services, established runner implementations,
and explicit, bounded storage.

**Start with [HANDOFF.md](HANDOFF.md).** It records the conversation's requirements,
accepted decisions, installed PoC state, proof links, remaining gaps and restart
commands. Linux jobs and cache reuse passed; macOS VM jobs are still pending.
The PoC is stopped for handoff. Existing runners have not been migrated.

The PoC packages an unchanged existing manager, runscaler, over Docker and
Tart, with systemd units on Bob and an Apple ServiceManagement registration
bridge on macOS. The accepted macOS approach is one disposable VM per job.
This repository owns installation and storage policy; a custom cross-platform
runner supervisor is not planned. Mac runtime storage is internal, under
`~/CI/github-actions-runner/`.

One CI storage root contains job workspaces, a few useful cache mounts
(initially Go modules, Go build output and the package store), and deliberately
retained artifacts. Worker images share installed tool layers. Node is requested
as `24`; patch releases are normal maintenance.

- [Design, reuse assessment and storage requirements](DESIGN.md)
- [Observed installations and disk usage](CURRENT.md)

Acceptance includes real jobs, native OS identity/lifecycle and demonstrated
storage reuse, cleanup and budgets.
