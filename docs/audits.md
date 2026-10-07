# Audits

Comment and doc quality needs a check: a rule in `CLAUDE.md` only helps if
something enforces it. Two audits do the checking, and `/ship` is where they run:

| Detector                 | Finds                              | Hands off to        |
| ------------------------ | ---------------------------------- | ------------------- |
| `audit-comments-gate.py` | Comment lines the branch added     | `Agent(audit-comments)` |
| `audit-docs-gate.py`     | Docs the branch touched            | `Agent(audit-docs)` |

`Skill(ship)` runs both with `--list --scope branch` before it commits, and
spawns a subagent only for a detector that reported something. A branch that
touched no comments and no docs therefore costs two script runs and nothing
else.

**It runs once per PR, not once per turn.** It is deliberately not a `Stop`
hook: firing at the end of every turn re-runs the same audit over the same
branch a dozen times per PR, which costs far more than it catches. `/ship` is
the one command that marks a PR, so the audit runs there.

The audit runs **before** the commit, not after the PR, so the edits it makes
land inside the commit that opens the PR rather than trailing it in a follow-up
push.

Neither audit asks the main session to do the work. Each goes to a subagent —
`agents/audit-comments.md` and `agents/audit-docs.md`, both pinned to `haiku` —
which runs the matching skill, applies the edits and reports back. Reading every
touched file in full is the expensive half of an audit, and the subagent keeps
it out of the main context.

The skills share the detectors via `--list`, so an audit covers exactly what was
reported. For comments that means a shallow scan for markers outside string
literals — `LINE_MARKERS` and `NAME_MARKERS` in the script are the list of file
types, and markdown is excluded since prose is not comments. For docs it means
the four well-known filenames (`CLAUDE.md`, `AGENTS.md`, `README.md`,
`REVIEW.md`) plus anything under a `docs/` tree. Generated and mechanical
markdown such as `CHANGELOG.md`, `LICENSE.md` and `CODE_OF_CONDUCT.md` is
excluded on purpose, because a detector that reports files nobody maintains
claim by claim teaches you to ignore it.

They do not chain. `audit-comments` moves system-level facts out of comments and
into markdown, which makes that file a touched doc — but the two run
concurrently, so the docs audit picks it up on the next `/ship`.

The two detectors are separate scripts so either can be dropped from `/ship`
alone. They share `_audit_gate.py` for the git half, so their scope semantics
cannot drift apart.
