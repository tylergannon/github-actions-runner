# Independent review: persistent runner tools and cleanup

## Review target

The current runner implementation and working changes in this worktree, plus consuming workflow changes in the runner-current-go worktrees for skgo, gimbal, skgo-project and gimbal-view. The authoritative target is README.md and the user's requirements: centralized execution, on-demand ordinary workers, permanently installed software, properly named OS services, bounded capacity, one declared CI root per host, scoped weekly cleanup and current stable Go beginning with 1.27.3.

The review was performed independently under the adversarial-review skill. No caller instructions narrowed defect scope. Implementation and runtime proof were still in progress when this snapshot was reviewed.

## Evidence inspected

- README.md, DESIGN.md, OPERATIONS.md, components.toml, the full current runner diff and surrounding scripts/fleet.py maintenance/status/service code.
- scripts/provision-tools.py, scripts/test_fleet.py, worker Dockerfile, Linux/Mac examples, fleet/host examples, native systemd definitions and signed Mac application entry points/plists.
- Pinned upstream runscaler provider/mount implementation and qualification workflow.
- All current consuming workflow diffs in the four named worktrees, their applicable AGENTS.md instructions, surrounding setup steps and tool manifests.
- Read-only inspection of deployed host manifests and manager capacity/storage configuration. Read-only inspection verified that Linux tool, mise and browser volumes bind below the declared protected tools directory, with separate architecture stores where needed. No credentials are reproduced here.
- Read-only inspection verified complete Go 1.27.3 installations for both Linux architectures and the declared Node installations, including an older exact compatibility patch requested by an existing manifest.
- Ran `python3 -m unittest discover -s scripts -v`: all nine tests passed. These include refusal to clean installed tool directories or their parent workspace, preservation of tools/evidence while deleting job data, restoration of services/routing after cleanup failure, and protection of configured worker/cleanup image tags.
- `git diff --check` passed for the runner and the inspected consuming worktrees.

## Findings

No material source or configuration findings were identified in this snapshot. No nitpicks are reported.

The cleanup guard at scripts/fleet.py:150-177 rejects overlap with tool stores, native runner installations, registration and prepared environments before cleanup. The same guard protects log targets at scripts/fleet.py:198-202. Image retention excludes configured worker images and the cleanup image at scripts/fleet.py:215-235. The provisioning script validates upstream SHA-256 checksums, installs architecture-specific Actions tool-cache entries and reuses completed installations. The consuming workflow changes select stable Go without changing module compatibility minimums.

## Proof boundary

This is a source/configuration review, not acceptance of the complete deployment. The caller explicitly reported ongoing base provisioning and pending runtime proof. I did not independently run a real workflow twice, perform fleet maintenance, run the workflow afterward, observe every consuming setup action reuse its installation, inspect the current Login Items UI, or measure idle resource use. Those remain the README acceptance evidence required before declaring the full setup delivered. Existing passing unit tests and cache sentinels do not establish those runtime claims.

Outcome: no findings
