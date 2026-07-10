# Fleet ops layer (khglynn) — how this fork stays patched

**Added 2026-07-08.** This fork is the vetted deploy source for Kevin's personal
Google Workspace MCP (Cloud Run). `main` = the exact upstream release we run,
plus this ops layer (additive files only — no code divergence from upstream).

The five questions, answered (the whole pipeline in one box):

| Question | Answer |
|---|---|
| What starts the work? | `fleet-release-watch` (daily cron) sees a new upstream release tag |
| Where does it run? | GitHub Actions on this fork (public repo → all security features free) |
| Where does it remember? | The sync PR itself + `.fleet/heartbeat.log` + pinned version in `pyproject.toml` |
| Where does a human approve? | Every sync PR: green `fleet-ci` gates + a 7-day aging window (label `security-override` + cite the CVE to fast-lane), then Kevin merges; deploys run from merged `main` only |
| How do we know output stayed good? | `fleet-ci` (tests, OSV lockfile scan, Trivy container scan, zizmor) + post-deploy `fitness-check.sh` + weekly 💓 heartbeat to Slack — silence ≠ green: no heartbeat two Mondays running means the pipeline itself is broken |

Companion pieces: Dependabot (grouped weekly updates + security alerts),
CodeQL default setup, secret scanning + push protection — all repo settings,
verified on. Deploy scripts + fitness check live in
`khglynn/self-hosted-mcps` → `deploy/`.
