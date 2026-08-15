---
name: audit-comments
description: Audit the code comments in the files a change touches — cut the ones a reader could derive from the code, rewrite the ones that will go stale, move the ones that belong in markdown, and match the conventions of the surrounding files. Use when the user says "audit comments", "check the comments", "review my comments", or after writing code that adds comments, before committing or opening a PR.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git ls-files:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(python3:*), Read, Edit, Glob, Grep
user-invocable: true
---

# Audit Comments

Review the comments in the files a change touches, and act on the verdict. This
is a quality pass over comments only — it does not look for bugs.

## The test

**Could the reader derive this themselves?** Not "is it true" or "is it
helpful" — *derivable*. If the answer sits in the code in front of them, in the
upstream module, or in the provider/library docs one search away, the comment is
noise and costs more than it gives.

A comment earns its place when the information lives **outside** what a
competent reader can reach: a constraint from another system, a workaround for
someone else's bug, a business rule, a decision whose reasoning isn't visible
from here.

Everything below is that test applied along a different axis.

## Behavior

- **Added comments are the trigger; every comment in a touched file is in
  scope.** If a comment you pass on the way fails a check, fix it too — a file
  you have already opened and read is the cheapest place this will ever be
  fixed. The boundary is the set of files the change touches; don't wander into
  files the change never opened.

  This is the deliberate exception to the usual "don't sweep the file for
  unrelated cleanup unless asked" rule. Invoking this skill *is* the asking.
- **Act, don't just report.** Apply the cuts and rewrites, then say what
  changed. `--dry-run` reports and edits nothing.
- **Convention beats preference.** Read the files around the change before
  judging style. A repo that writes `// eslint-disable-next-line` one way, or
  puts a docstring on every public function, wins over anything in this skill.
- **When you can't tell whether a comment is load-bearing, keep it and say so.**
  Deleting a comment that encoded something nobody remembers is the one
  expensive mistake available here.
- **Honour `$ARGUMENTS`:**
  - *(none)* — everything the branch adds over its base, committed and not.
  - `--staged` — the staged diff only.
  - `--working` — uncommitted changes only.
  - `<PR number or URL>` — audit that PR's diff.
  - `<path>…` — restrict to those files.
  - `--dry-run` — report the verdicts, change nothing.

## Checks

| # | Check | The question | When it fails |
| - | ----- | ------------ | ------------- |
| 1 | Derivable | Could a competent reader get this from the code, the upstream module, or the docs one search away? | **Cut** |
| 2 | True | Does it describe what the code does *now*, not what it did two edits ago? | **Rewrite**, or cut if the fact is gone |
| 3 | Durable | Will it still be true in six months with nobody maintaining it? | **Rewrite** — keep the direction, drop the measurement |
| 4 | Consistent | Does it look like the comments in the files around it? | **Rewrite** |
| 5 | Short | Is it as short as the fact allows? | **Rewrite** |
| 6 | Placed | Is it next to the thing it explains? | **Move** |
| 7 | About the code | Is it about the code, or about the act of changing the code? | **Cut** |
| 8 | Right medium | Is this about *this code*, or about how the system fits together? | **Move to markdown** |

### 1. Derivable

The clearest failure case is Terraform — a comment above a variable explaining
what that variable is for. The name says it, and the upstream module says the
rest:

```hcl
# The number of days to retain backups     <- cut: derivable from the name
variable "backup_retention_days" {}

# Altinity's operator ignores values below 3 — silently clamps to 3.
variable "shard_count" {}                  <- keep: you cannot know this
```

Same shape in every language:

```python
# Loop over the players and sum their scores    <- cut
for player in players: ...

# Transaction pooler: prepared statements break across pooled connections.
prepare_threshold=None                          <- keep
```

**Docstrings are welcome where they earn their place.** A function whose
purpose, contract, units, or failure modes aren't obvious from the signature
should have one. What it must not do is restate the signature in prose —
`Args: player_id — the player id` is the same derivability failure in a
different shape. Cut the restated half, keep the part that surprises the caller.

### 2. True

The comment and the code drifted. Usually because the code was edited and the
comment above it wasn't:

```python
# Retries three times with exponential backoff
@retry(attempts=5, backoff="linear")
```

Check every comment adjacent to modified code, not just the added ones. This is
the one place where a pre-existing comment is in scope.

### 3. Durable

A measured figure in a comment is a claim with a timestamp attached that nothing
will ever update. Keep the *direction*, drop the *magnitude*:

```python
# Prune images before build cache — reversed, this leaves 10.3 GB behind   <- rewrite
# Prune images before build cache; the reverse order orphans most of it    <- keep
```

Volatile, cut or generalise: benchmark timings, throughput, memory or cost
figures, row and record counts, line numbers and file offsets, dates, "for
now" / "currently" / "as of today", counts of things that live in another repo,
and our own version numbers.

Durable, keep the number: a hard limit another system imposes (a page-size cap,
a provider clamp, a protocol maximum), a business rule, a named upstream bug
with an issue link. These don't drift when our code changes, which is exactly
what makes them worth writing down.

`TODO` and `FIXME` with no owner and no ticket are permanent litter — either
give them a ticket reference or do the work.

### 4. Consistent

Before judging style, read two or three neighbouring files that this change did
*not* touch, in the same language and directory. Match what they do on:

- whether comments sit above the line or trail it
- sentence case vs lowercase, full stops or not
- docstring presence and format (Google, NumPy, reST, one-liner)
- how ignores and pragmas are annotated
- comment density — a file with none is telling you something

A correct comment in the wrong house style still reads as foreign.

### 5. Short

One line if the fact fits on one line. A paragraph only when the reasoning
genuinely needs it — a cross-system constraint with a consequence, a decision
with a rejected alternative. Prose that restates the same point three ways is
one point.

The usual cause of a wall of text is a comment doing two jobs: a real
non-derivable fact wrapped in narration of the code beneath it. Keep the fact,
delete the narration, and it lands in a line or two.

### 6. Placed

A comment explaining a constraint belongs on the line that carries it, not in a
file header three hundred lines away. A file-level docstring describing one
function belongs on that function.

### 7. About the code

Git already records the change, and these go stale the moment anything moves:

- `# updated to use the new client`, `# added for MUL-299`
- tombstones for removed code: `# (old implementation deleted)`
- commented-out code — delete it
- section banners: `# ===== HELPERS =====`
- addressing the reader: "Note that we…", "As you can see…"

### 8. Right medium

**Comments describe code. Markdown describes the system.** A comment is read by
someone already looking at that line — it can only ever explain the thing it
sits on. The moment a fact is about how parts fit together, it is in the wrong
medium: nobody reads a `.py` file to learn the architecture, so a fact buried
there reaches only the people who least need it.

A comment is in the wrong medium when it explains:

- how two services, repos or accounts talk to each other
- a workflow or sequence spanning more than this file
- a convention future work is expected to follow
- a decision with consequences beyond the function it sits on
- setup, deployment, or how to run the thing

Where it goes instead:

| The fact is… | It belongs in |
| ------------ | ------------- |
| a rule an agent must follow in this repo | `AGENTS.md` / `CLAUDE.md` |
| how the pieces fit, or why they're arranged that way | `docs/` |
| how to install, configure or run it | `README.md` |

Move it, don't duplicate it. Then either leave nothing behind, or leave a one
line pointer if the code genuinely needs the reader to know the doc exists.

Stop once the fact is in the right file. Don't audit the destination from here —
writing to it makes it a touched doc, which is what the `audit-docs` gate keys
on, so it gets its own pass with its own rules rather than a borrowed one.

The narrow case still belongs in the code: a constraint that happens to come
from another system, but which only affects *this line*, is a comment.
`prepare_threshold=None` needs the pooler explanation right there. What the
pooler is and why we use one is `docs/`.

## Workflow

### Step 1: Resolve the scope

Default is the whole branch — what a PR reviewer would see:

```
!git branch --show-current
!git symbolic-ref --short refs/remotes/origin/HEAD
```

Strip the `origin/` prefix; **never assume `main`**. If `$ARGUMENTS` names a PR,
use `gh pr diff <n>` instead and skip to step 3.

### Step 2: List the added comment lines

The Stop hook and this skill share one detector, so an audit covers exactly what
the hook flagged:

```
!python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/audit-comments-gate.py" --list --scope branch
```

`--scope working` for uncommitted only, `--scope staged` for the index. Trailing
paths restrict it. Output is `path:line<TAB>text`.

Detection is shallow by design — it finds candidates, it does not judge them. A
`#` inside a string that slipped through is a finding you dismiss, not a bug.

If it returns nothing, say so and stop.

### Step 3: Read the surroundings

Read each touched file **in full**, not just the neighbourhood of each finding.
Two reasons: a comment cannot be judged from the diff — the derivability test is
about what the reader can see on the page — and every other comment in that file
is in scope, so you need to have seen them.

Then read two or three untouched neighbours in the same directory and language,
for the convention check.

### Step 4: Judge

One verdict per comment: **keep**, **rewrite**, **cut**, **move**, or
**to markdown**. Name the check that failed. If nothing failed, it's a keep —
say nothing further about it.

Judge three sets, in this order:

1. The comments the detector listed.
2. Comments adjacent to modified code, for check 2 — the edit may have just
   falsified them.
3. Every other comment in the touched files. Hold these to the same checks, but
   report them separately: the user asked for a change, and comments they didn't
   write moving in the same diff should be visible as a distinct group.

### Step 5: Apply

Make the edits, unless `--dry-run`. Cuts and rewrites only — do not touch the
code the comments sit on. If a comment is only fixable by renaming the thing it
describes, say that instead of doing it; the rename is a separate change.

For anything judged **to markdown**, write it into the destination doc and stop
there. Auditing that doc is `audit-docs`' job, and touching it is what arms that
gate.

### Step 6: Report

Group by verdict, one line each, path:line first. Keeps are a count, not a list.
Comments the change didn't add go in their own group, so the user can see what
moved that they didn't write:

```
Audited 11 added comments across 4 files, plus 23 already in those files.

Cut (5)
  clients/clickhouse.py:41   "# build the query" — derivable
  clients/clickhouse.py:88   "# added for MUL-299" — narrates the change
  ...

Rewrote (3)
  clients/redis.py:22        dropped "takes about 300ms" — a measurement, keep the ordering claim
  ...

Moved to markdown (1)
  clients/livescoring.py:8   the two-Supabase-project explanation → docs/02-data-sources.md

Pre-existing, same files (2)
  clients/redis.py:104       cut "# returns a dict" — derivable
  clients/redis.py:140       rewrote: said 3 retries, the decorator says 5

Kept 3. Left alone: infra/main.tf:14, load-bearing but I can't tell why —
"must run before the NAT gateway" with no reference.
```

## Notes

- **`Skill(ship)` is the automatic half.** It runs
  `scripts/audit-comments-gate.py --list --scope branch` before committing, and
  spawns the `audit-comments` subagent only if that reported something — which
  is where the Haiku pin lives, so you may be reading this as that agent rather
  than in the session that wrote the comments. Auditing once per PR rather than
  once per turn is deliberate: the turn-by-turn version cost far more than it
  caught.
- **The audit runs before the commit**, so its edits land inside the commit that
  opens the PR instead of trailing it.
- **Which file types count is the script's business**, not this document's —
  `LINE_MARKERS` and `NAME_MARKERS` in `audit-comments-gate.py` are the list.
  Markdown is deliberately not among them: prose is not comments, and it has its
  own skill. A type the script doesn't know is invisible to `/ship`, but
  `/audit-comments <path>` still audits it on demand.
- `Skill(audit-docs)` is the counterpart, and check 8 is the seam. They do not
  call each other: a fact moved into markdown makes that file a touched doc, and
  the `audit-docs` gate picks it up on its own.
