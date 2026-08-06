---
name: audit-comments
description: Audit the code comments added by the current change — cut the ones a reader could derive from the code, rewrite the ones that will go stale, and match the conventions of the files around them. Use when the user says "audit comments", "check the comments", "review my comments", or after writing code that adds comments, before committing or opening a PR.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git ls-files:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(python3:*), Read, Edit, Glob, Grep
user-invocable: true
---

# Audit Comments

Review every comment the current change adds, and act on the verdict. This is a
quality pass over comments only — it does not look for bugs.

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

- **Judge only what this change added.** A comment that was already there and
  wasn't touched is out of scope, however bad. The exception is a comment
  sitting next to code this change modified — if the edit made it wrong, it is
  now this change's problem.
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
  - `--working` — uncommitted changes only. This is what the Stop hook uses.
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

Two reads per file, both necessary:

- **The file itself**, around each finding. A comment cannot be judged from the
  diff — the derivability test is about what the reader can see on the page.
- **Two or three untouched neighbours** in the same directory and language, for
  the convention check.

### Step 4: Judge

One verdict per comment: **keep**, **rewrite**, **cut**, or **move**. Name the
check that failed. If nothing failed, it's a keep — say nothing further about
it.

Also sweep comments adjacent to modified code for check 2, even though the
detector didn't list them.

### Step 5: Apply

Make the edits, unless `--dry-run`. Cuts and rewrites only — do not touch the
code the comments sit on. If a comment is only fixable by renaming the thing it
describes, say that instead of doing it; the rename is a separate change.

### Step 6: Report

Group by verdict, one line each, path:line first. Keeps are a count, not a list:

```
Audited 11 added comments across 4 files.

Cut (5)
  clients/clickhouse.py:41   "# build the query" — derivable
  clients/clickhouse.py:88   "# added for MUL-299" — narrates the change
  ...

Rewrote (3)
  clients/redis.py:22        dropped "takes about 300ms" — a measurement, keep the ordering claim
  ...

Kept 3. Left alone: infra/main.tf:14, load-bearing but I can't tell why —
"must run before the NAT gateway" with no reference.
```

## Notes

- **The Stop hook is the automatic half.** `scripts/audit-comments-gate.py` runs
  on `Stop`, scans the uncommitted working tree, and blocks once per commit per
  session if comments were added. It scopes to the working tree rather than the
  branch so a long-lived branch's existing comments don't get re-litigated every
  session; the slash command is the one that covers the whole PR.
- **`AUDIT_COMMENTS_HOOK=0` disables the hook** for a session without touching
  settings.
- **Languages covered**, by marker:

  | Marker | Extensions |
  | ------ | ---------- |
  | `#` | `.py` `.pyi` `.sh` `.bash` `.zsh` `.rb` `.pl` `.r` `.yml` `.yaml` `.toml` `.graphql` `.gql` `.ex` `.exs` `.nix` `.jl` `.ps1` `.conf` `.properties`, and `#`/`;` for `.ini` `.cfg` |
  | `//` | `.js` `.mjs` `.cjs` `.jsx` `.ts` `.tsx` `.go` `.java` `.kt` `.swift` `.c` `.h` `.cc` `.cpp` `.hpp` `.rs` `.scala` `.cs` `.dart` `.proto` `.prisma` `.groovy` `.gradle` `.scss` `.less` `.vue` `.svelte` |
  | `--` | `.sql` `.lua` `.hs` |
  | both `#` and `//` | `.tf` `.tfvars` `.hcl` `.php` |
  | `/* … */` only | `.css` (plus block comments in every `//` language above) |
  | `<!-- … -->` | `.html` `.htm` `.xml` `.vue` `.svelte` |
  | by filename | `Makefile` `Dockerfile` `Justfile` `Procfile` `Brewfile` `.envrc` `.gitignore` `.dockerignore` `.editorconfig` |

  Python docstrings (`"""`/`'''` openers) count as comments. Markdown, JSON and
  lockfiles are skipped — prose is not comments, and the other two have none.
  Anything not listed is invisible to the hook; add it to `LINE_MARKERS` in
  `audit-comments-gate.py`. `/audit-comments <path>` still works on an
  unlisted file, it just won't be found automatically.
- The hook fires once per `session + HEAD`, so committing re-arms it for the
  next batch of work. State lives in `~/.claude/state/audit-comments/` and is
  swept after seven days.

## Examples

`/audit-comments`

1. Resolve base, list added comments across the branch
2. Read each site plus two neighbours per directory
3. Cut the derivable ones, rewrite the ones carrying figures, report

`/audit-comments --dry-run`

1. Same audit, no edits — a verdict list only

`/audit-comments 42`

1. `gh pr diff 42`, audit what that PR adds, report without editing (the branch
   may not even be checked out)
