correction: The user's centralized GitHub Actions requirement never required disposable per-job workers. Required software must remain installed across jobs and weekly cleanup.
decision: README.md now defines the intended behavior and repository scope. Implementation changes are deferred to subsequent work, as requested by the user.
correction: Weekly cleanup targets accumulating caches, build output, temporary files and expired artifacts/logs; it must preserve software, registration and configuration and avoid active jobs.
decision: Proper GitHub Actions Runner identity in OS background settings, explicit runner capacity and a declared CI data root per host are requirements, not optional follow-up work.
doc_bug: DESIGN.md and OPERATIONS.md still describe the disposable-worker proof of concept. README.md explicitly marks them as existing implementation documents pending reconciliation.
