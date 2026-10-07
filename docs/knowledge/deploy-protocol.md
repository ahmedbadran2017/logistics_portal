---
name: deploy-protocol
description: Ahmed runs production deploys himself — Claude must NOT trigger /usr/bin/update
metadata: 
  type: feedback
---

As of 2026-09-10 Ahmed instructed: "ماتعملش انت اي ديبلوي تاني على السيرفر" — do NOT run deploys on the production server. Earlier the same week he had delegated deploys to me; that is revoked.

**Why:** deploys collide on `bench_build.lock` when run concurrently with his own runs, restart containers (killing in-flight MCP calls), and flush redis. He wants control of the timing.

**How to apply:** after commit+push, tell Ahmed the change is pushed and waiting for HIS deploy (`/usr/bin/update` on the server). Never run `ssh … /usr/bin/update` myself unless he explicitly re-authorizes it for a specific deploy. Note migrations that are heavy (e.g. index builds on big tables) so he can pick quiet hours. Related: [logistics-portal-project](logistics-portal-project.md).
