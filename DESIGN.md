# Runner infrastructure requirements

This repository owns native service definitions, worker images, example
configuration and storage policy. Installed services must work independently
of a mutable source checkout. Application repositories own build commands and
decide which outputs constitute useful evidence.

## Reuse and native ownership

Use established runner implementations rather than writing another supervisor.
The PoC packages unchanged runscaler at the revision in `components.toml`,
using its Docker and Tart providers. The Swift bridge only registers an embedded
LaunchAgent through Apple's SMAppService; it does not control worker lifecycle.
The macOS app includes an icon and supports code signing with the operator's
identity. Verify the actual System Settings attribution after installation.

systemd or launchd owns the manager's lifecycle. The manager owns disposable
workers. Do not add a competing Docker restart policy or shell restart loop.
Native start, stop, enable/disable, update and startup behavior must be verified.
A stop must handle real children, and recovery must reconcile owned leftovers.

## Disposable execution

Linux jobs use Ubuntu-based disposable Docker containers, with explicit CPU,
memory and process limits. macOS jobs use fresh disposable Tart macOS VMs on
Apple hardware. Docker on macOS cannot qualify Darwin, Xcode or Apple signing.
Export useful evidence, stop each worker, and remove its writable environment.

The examples scale from zero to one worker. Final concurrency is an explicit
capacity choice supported by measurements. Preserve repository routing and
private qualification boundaries during an incremental migration. Do not
recreate old workers until important writable-layer state has been accounted for.

## Visible, owned storage

Keep CI data under one obvious parent per host. OS app bundles and native
registrations retain their normal installation locations. Use internal Mac
storage; make room before growing images rather than moving CI to a backup disk.

Start with three purposeful shared caches: Go modules, Go build output and the
package store/metadata used by Vite+. Workspaces, temporary HOME directories
and application dependencies such as `node_modules` are disposable per job.
Add persistent caches only for a demonstrated benefit. Signing secrets do not
belong in a reusable VM base.

Every persistent category needs an owner, visible usage, a budget and a removal
rule: caches, images/layers, Docker build cache, golden VMs, clones, artifacts
and logs. A bind mount is not a quota; weekly reset is not instantaneous capacity
protection. Account for Docker's engine-owned storage separately from bind mounts.
On shared engines, cleanup must not prune unrelated applications or services.

Retention must cover success, failure, cancellation and interruption. Export
useful diagnostics rather than retaining entire execution homes. Prefer existing
filesystem limits, cache tools and native scheduled cleanup over a new controller.

## Toolchains

Request Node as `24` and record resolved versions in diagnostics. Routine patch
upgrades should not require editing every application workflow. Keep GitHub's
bundled Node runtimes, which execute JavaScript Actions independently of build
Node. The Linux example uses Go `1.27`; this is not an exact shared patch policy.
Use `vp install`, `vp run`, `vp exec` and `vp dlx` for frontend work.

Container layers and cloned VM bases share installed tools. Avoid unexplained
independent installations per persistent worker. Component revision/checksum
pins establish provenance and differ from routine application patch pins.

## Qualification and public boundaries

Prove real GitHub execution, distinct successive workers, fresh HOME state,
cache reuse, disposal and native OS identity. Test failure/cancellation and
interruption, busy stop, updates and startup. Verify enforced storage budgets,
artifact retention and real release signing before production adoption.

Keep machine inventories, local installation details, credentials, execution
logs and screenshots out of this public repository. The example qualification
workflow belongs in a private execution repository. Register self-hosted capacity
there, and admit only trusted code; disposable workers still share the host's
network and selected caches. Do not attach self-hosted capacity to public PR
execution as part of adopting these examples.

Known PoC limitations include warning-only Linux cache budgets, missing shared
macOS cache mounts, and an upstream startup check that can misclassify very short
successful Mac jobs as startup failures. The qualification workflow waits through
that observation window; it does not fix the manager defect. Compilation/signing
of a small binary is not application release qualification.
