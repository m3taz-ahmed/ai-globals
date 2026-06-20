[WORKFLOW] 04-deployment
[OBJ] Deployment and Release protocol.
[RULES]
1. [REQ] Pre-Deploy: Verify tests pass, DB migrations tested on staging, cache cleared, assets built.
2. [REQ] Deploy: `down` -> `pull` -> `composer/npm install` -> `migrate` -> rebuild cache -> restart queues -> `up`.
3. [REQ] Rollback: `down` -> `git checkout v[prev]` -> rollback migrations (if safe) -> `install` -> `up` -> Document post-mortem.
4. [REQ] Health: Verify HTTP 200 on `/health`, core flows work, no Sentry spikes.
