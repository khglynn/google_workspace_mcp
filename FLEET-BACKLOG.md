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
