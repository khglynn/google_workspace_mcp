# Fleet backlog

Fork-owned work items that are not urgent enough to block a sync but should not
be lost. This file exists because **issues are disabled on this fork**, so there
is no tracker to file them in. If issues are ever enabled, migrate these to real
issues and delete the file.

Nothing here is upstream's concern — do not send these upstream unless a note
says so explicitly.

---

## Privacy pass: user email addresses in auth-layer logs

**Opened 2026-08-02** (surfaced during the upstream v1.23.0 sync, PR #11).

CodeQL reports `py/clear-text-logging-sensitive-data` across the auth layer —
**54 open alerts on `main`** as of 2026-08-02, all the same rule. The v1.23.0
sync PR appeared to add 35 "new" ones; it did not. Those were pre-existing
alerts re-attributed because the merge shifted line numbers in files it touched
(verified: the `Auth failed for {user_google_email}` statement sits at
`auth/service_decorator.py:956` on `main` and `:989` on the sync branch — a pure
line shift, identical code).

**What the rule is actually objecting to:** statements that log
`user_google_email`. CodeQL's taint tracker labels the value `password` because
it flows out of an OAuth code path; the value logged is a user's email address,
used for multi-user session routing. So the alert text overstates it — there is
no credential in the logs — but the underlying question is real: this deployment
writes end-user email addresses into logs at `info` level across
`auth/service_decorator.py`, `auth/oauth21_session_store.py`, and
`auth/google_auth.py`.

**Why it is worth a deliberate pass rather than a quick fix:**

- These logs are load-bearing for debugging multi-account routing, which is the
  fork's main reason to exist. Blanket-removing them trades one problem for
  another.
- The alerts are upstream code, so any fix either diverges from upstream (a
  permanent merge-conflict surface on every sync) or goes upstream as a PR.
  Decide which before writing code.
- 54 alerts of one noisy rule also means the CodeQL signal for this repo is
  effectively saturated — a genuine new alert of this class would be easy to
  miss in the pile. Fixing or suppressing deliberately restores the signal.

**Options to weigh when it comes up:** redact to a stable hash or the domain
part for routing-debug purposes; drop the identifier to `debug` level; or add a
scoped CodeQL suppression with a written rationale if the current behavior is
accepted on purpose. Any of the three is fine — the thing to avoid is leaving 54
alerts open and unexamined, which is indistinguishable from not looking.

**Not a blocker for:** upstream syncs. This predates v1.23.0 and is unchanged
by it.

**Update 2026-09-23 (v1.28.0 sync, PR #22):** 55 open on `main`, and the sync
PR adds 5 more of the same rule, but a different flavor: they fire on names,
not emails. `auth/oauth_proxy_config.py:28/33/36` log a setting name containing
"TOKEN" and a number of seconds; `auth/google_auth.py:282/284` log a
client-secrets file path and load errors that contain only that path. All five
are false positives. Same decision as above applies.

---

## Port `calendar_acl_list` to main before moltshg is redeployed

**Opened 2026-09-23** (v1.28.0 sync, PR #22). moltshg runs from the unmerged
branch `remembrall/calendar-acl-list` (NOW.md, 2026-08-25). The tool (`b57e4b3`:
appended code in `gcalendar/calendar_tools.py` plus the `calendar.complete`
line in `core/tool_tiers.yaml`) has no upstream equivalent in v1.28.0, so a
deploy from main removes it, and `fitness-check.sh` has no tool-inventory check
that would notice. Port it in its own PR. Upstream changed both files many
times since the branch was cut, so expect to rewrite rather than cherry-pick.

Do **not** cherry-pick `77e1af8` (the token-TTL half of that branch). Upstream
v1.25.2 ships the same settings as `WORKSPACE_MCP_OAUTH_PROXY_ACCESS_TOKEN_EXPIRY_SECONDS`
/ `..._TOKEN_EXPIRY_THRESHOLD_SECONDS` (the fleet env files carry both names
since meta-repo `e2de41c`), and `77e1af8` passes those keywords explicitly next
to upstream's `**expiry_kwargs` in `core/server.py`, which is a duplicate-keyword
TypeError at boot. Once every account runs main, drop the three older names
from the env files.

## Enforce merge commits for sync PRs

**Opened 2026-09-23.** The v1.23.0 sync (#11) was squash-merged, so git kept
v1.22.2 as the merge base and every later intake hit 21 conflicting files. The
recipe now says "merge commit, never squash", but the repo still allows
squash. `allow_squash_merge=false` in repo settings enforces it (Dependabot PRs
merge fine as merge commits). Kevin's call; it's a repo setting, not code.

## Dependabot: ignore semver-major for fastmcp, fastmcp-slim, mcp

**Opened 2026-09-23.** Upstream's `fastmcp>=3.4.7` has no upper bound, so
Dependabot can propose fastmcp 4.x / mcp 2.x, majors upstream has not adopted.
An `ignore` rule with `update-types: ["version-update:semver-major"]` for those
three keeps the lock on what upstream tests; take majors through a sync instead.
