correction: The user's centralized GitHub Actions requirement never required disposable per-job workers. Required software must remain installed across jobs and weekly cleanup.
decision: README.md now defines the intended behavior and repository scope. Implementation changes are deferred to subsequent work, as requested by the user.
correction: Weekly cleanup targets accumulating caches, build output, temporary files and expired artifacts/logs; it must preserve software, registration and configuration and avoid active jobs.
decision: Proper GitHub Actions Runner identity in OS background settings, explicit runner capacity and a declared CI data root per host are requirements, not optional follow-up work.
doc_bug: DESIGN.md and OPERATIONS.md still describe the disposable-worker proof of concept. README.md explicitly marks them as existing implementation documents pending reconciliation.
correction: Persistent installations do not require permanently running workers. User explicitly chose to retain runscaler's zero-idle container/VM execution while preserving installed software in prepared environments and protected tool storage.
decision: Use Go 1.27.3 as the baseline and prefer current stable releases. Older go.mod minimums do not require the older compiler; explicit setup-go version requests are a separate source of repeated downloads.
friction: The installed fleet is ahead of main on open PR 4. Continue its existing native app and maintenance implementation rather than recreating them from the stale main checkout.
doc_bug: Installed native cleanup policies include _work/_tool or its parent, deleting tool installations weekly. Protect installations in fleet.py and narrow those deployed cleanup paths.
friction: A tool volume below an absent _work makes Docker create _work as root, failing jobs before steps with UnauthorizedAccessException for _work/_temp. Prepare runner-owned work and HOME mount parents in the image before deploying nested software mounts.
