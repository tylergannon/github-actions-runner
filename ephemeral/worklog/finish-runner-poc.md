# Runner PoC continuation

- decision: Continue the authorized PoC before production migration. The initial PR #1 is already merged; this continuation uses a new worktree and PR.
- correction: User requires deleting HANDOFF.md before merge. Preserve useful operating instructions and proof in README instead of retaining a temporary handoff.
- evidence: Native SMAppService registration succeeded without an approval prompt; launchd reports the signed parent bundle and running manager. System Settings attribution and real VM jobs still need observation.
- evidence: Workflow 39871482145 passed all four jobs on initial main 08624fd. Two Mac clones were removed; System Settings visibly showed the exact app name. This establishes basic PoC execution, not production adoption.
- friction: Pinned runscaler classifies a runner that exits during its five-second startup settling check as a startup failure even if GitHub already completed its job successfully. Keep success-job evidence distinct from manager log health; proof jobs now survive that observation window. Upstream remediation remains necessary.
- decision: Route macOS manager diagnostics through upstream's 10 MiB rotating log with one backup under the owned root. Discard duplicate launchd console streams rather than accumulating unbounded stdout/stderr files.
