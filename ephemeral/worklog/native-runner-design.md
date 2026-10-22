# Native runner design

correction: User rejects home-directory runner sprawl, opaque runsvc.sh identity, automatic patch pinning and premature implementation. Design first; shared Node request is 24.
decision: User requests a separate repository that owns legitimate, recognizable macOS launchd and Linux systemd integration. Design scope includes both hosts; no production migration is authorized by this design checkpoint.
friction: Generic launchd Label changes do not establish System Settings attribution. Use an owning app bundle and ServiceManagement registration, then inspect the installed item.
discovery: Bob has eleven runner containers plus one native qualification runner. Four older containers belong to skgo-project, not skgo. Their registration state has no inspected host mounts; preserve their writable layers until migration ownership is understood.
decision: Preserve Ubuntu container compatibility on Arch Bob while proposing one native systemd service per instance and one host restart authority. Existing user-manager lingering is enabled.
correction: Tool duplication and bundled runner Node are different concerns; Docker image layers also share storage. Do not equate worker count with copies of every runtime byte.
discovery: Bob's native qualification runner tree reports 57 GiB, skgo cache tree 41 GiB and Gimbal cache tree 15 GiB. These aggregate observations need itemization before any reclamation claim or deletion.
