---
name: audit-docs
description: Audit the markdown a change touches — CLAUDE.md, AGENTS.md, README.md, REVIEW.md and anything under docs/. Cuts what the repo already says, verifies every claim against the code, and puts each fact in the doc that owns it. Use when the user says "audit docs", "check the docs", "review the README", after editing any markdown, or when Skill(audit-comments) moves a fact out of a comment.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git ls-files:*), Bash(gh pr diff:*), Bash(ls:*), Bash(test:*), Bash(rg:*), Bash(grep:*), Bash(find:*), Read, Edit, Glob, Grep
user-invocable: true
---

# Audit Docs

Review the markdown a change touches, and act on the verdict. The counterpart to
`Skill(audit-comments)` — same instinct, different medium.

## The test

For a comment, the question is *could the reader derive this from the code?* For
a doc it inverts. A doc exists precisely to hold what the code cannot say, so
the question is:

**Is this the doc that owns this fact, and is the fact still true?**

Docs fail differently from comments. A comment's usual failure is being
redundant on the day it was written. A doc's usual failure is being *correct on
the day it was written and wrong six months later*, with nothing to catch it —
no compiler, no test, no reviewer who would notice. Weight the audit
accordingly: **verification matters more here than concision.**

## Behavior

- **Verify, don't assume.** Every path, command, flag, target, filename and
  cross-repo claim gets checked against the repo before it passes. A doc that
  reads well and is wrong is worse than no doc — it is trusted.
- **Act, don't just report.** Apply the cuts, corrections and moves, then say
  what changed. `--dry-run` reports and edits nothing.
- **The whole file is in scope**, not just the changed lines. A doc is read
  start to finish; a section that contradicts the one the change added is now
  the change's problem. This is the deliberate exception to "don't sweep the
  file for unrelated cleanup" — invoking this skill is the asking.
- **Never invent a fact to fill a gap.** If a section is thin and you don't know
  the answer, say the gap exists. Fabricated documentation is the one failure
  here that cannot be caught by reading the doc.
- **Honour `$ARGUMENTS`:**
  - *(none)* — the docs the branch touches: `CLAUDE.md`, `AGENTS.md`,
    `README.md`, `REVIEW.md` and anything under `docs/`. Other markdown, a
    `SKILL.md` included, needs an explicit path.
  - `<path>…` — audit those files.
  - `--all` — every doc in the repo. Say up front this is the expensive one.
  - `<PR number or URL>` — audit that PR's markdown.
  - `--dry-run` — report the verdicts, change nothing.

## Which doc owns what

Most doc problems are a fact in the wrong file. Each of these answers a
different reader's question, and a fact belongs in **exactly one**:

| Doc | The reader's question | Belongs there |
| --- | --------------------- | ------------- |
| `AGENTS.md` / `CLAUDE.md` | "What are the rules here?" | Conventions to follow, targets to use, traps to avoid. Instructions, not background. |
| `README.md` | "How do I install and run this?" | Setup, install, the entry points, what it is in two lines. |
| `docs/` | "How does this fit together, and why?" | Architecture, data flow, decisions and their reasoning, cross-system integration. |
| `REVIEW.md` | "What should I look at?" | Review scope and standing concerns. |

The same fact in two of them is worse than in neither: they drift, and the
reader has no way to tell which is stale. Keep one, link from the other.

`AGENTS.md` and `CLAUDE.md` cost context on **every turn of every session** in
that repo. That is what makes length a correctness issue there and not a matter
of taste — a paragraph of background in `AGENTS.md` is billed thousands of times.
When in doubt, it goes to `docs/` and `AGENTS.md` links to it.

## Checks

| # | Check | The question | When it fails |
| - | ----- | ------------ | ------------- |
| 1 | True | Does every claim match the repo as it is right now? | **Correct**, or cut if the thing is gone |
| 2 | Resolvable | Do the links, paths and commands exist? | **Fix** |
| 3 | Right file | Does this doc own this kind of fact, and does it say it only once? | **Move**, or replace with a link |
| 4 | Derivable | Could the reader get this from the repo itself in one look? | **Cut** |
| 5 | Durable | Will it still be true in six months with nobody maintaining it? | **Rewrite** — keep the shape, drop the measurement |
| 6 | Short | Is it as short as the content allows, and is it earning its context cost? | **Rewrite** |
| 7 | Consistent | Does it look like the docs beside it? | **Rewrite** |
| 8 | Not a changelog | Is it about the system, or about the act of changing it? | **Cut** |

### 1. True

The check that justifies the skill. Go claim by claim and confirm against the
repo — do not pattern-match on plausibility:

- **Paths and filenames** — `ls` or `test -f` them. Renames leave docs behind.
- **Commands, targets, flags** — the `make` target exists in the `Makefile`, the
  flag exists in the script's arg parsing, the npm script is in `package.json`.
- **Names** — variables, resources, tables, env vars, queue and bucket names.
  These change quietly and the doc keeps the old one.
- **Counts and lists** — "three ingest sources", "the four apps". Count them.
  Lists that were exhaustive when written rarely still are.
- **Behavioural claims** — "X falls back to Y", "the hook fires once per Z".
  Read the code and confirm, or mark it unverified rather than passing it.

Where the doc and the code disagree, the code wins — but say so in the report
rather than silently rewriting, because occasionally the doc is describing
intent the code failed to implement, and that's a bug, not a doc error.

### 2. Resolvable

Relative links between docs, links into code, anchors, and image paths. A
`docs/` tree that has been reorganised leaves a field of broken links and
nothing complains. Check the target exists; for anchors, check the heading is
still spelled that way.

### 3. Right file

Apply the ownership table. The common failures:

- Architecture in the README, where it pushes setup below the fold.
- Setup steps in `AGENTS.md`, where they cost context every turn and duplicate
  the README.
- The same table in two files.
- A `docs/` page that is really a rule an agent needs — those belong in
  `AGENTS.md`, or at least linked from it, or nothing will read them.

When moving, leave a link if the reader of the original would genuinely go
looking; otherwise leave nothing.

### 4. Derivable

Weaker than the comments version — a doc restating something visible in the repo
is often doing real work by collecting it in one place. It fails only when the
repo says it *better*:

- a file tree that `ls` prints, and which goes stale immediately
- an API surface that the type definitions state exactly
- an option list already in `--help` or the argument parser
- a summary of a config file, next to a link to the config file

Keep the version that cannot go stale: link to the source of truth, and use the
doc for what the source of truth can't say — why it's shaped that way, which
option to reach for, what bites.

### 5. Durable

Same rule as comments, and docs violate it more. Volatile: timings, sizes,
costs, row counts, dates, "currently", "recently", "for now", version numbers of
our own code, and anything phrased relative to the moment of writing.

Durable: a limit another system imposes, a business rule, a decision and its
reasoning, a named upstream bug with a link.

A number that is genuinely useful and genuinely volatile can stay if it is
labelled as a snapshot rather than a fact — "roughly 1.5 GB at the time of
writing" survives contact with reality in a way "1.5 GB" does not.

### 6. Short

Cut padding, restated headings, and sentences that announce what the next
section will say. For `AGENTS.md` and `CLAUDE.md` specifically, apply the
context-cost test: **would you pay for this paragraph on every turn?** If it is
background rather than instruction, it goes to `docs/` and gets linked.

Prose that could be a table usually should be, when there are several things
being compared. A two-row table should be two sentences.

### 7. Consistent

Read the sibling docs before judging. Match heading depth and casing, table vs
bullet conventions, code-fence language tags, whether commands are shown with a
`$` prefix, British vs American spelling, and how paths are formatted. A
correct page in a foreign style reads as bolted on.

### 8. Not a changelog

Git records the change:

- "Updated to use the new client", "as of PR #22", "recently added"
- migration notes for a migration that finished
- "New in v2" for a v2 that shipped two years ago
- tombstones: "(the old approach used X)" — unless the reason it was abandoned
  is the point, in which case say *that*, in the present tense

## Workflow

### Step 1: Resolve the scope

```
!git branch --show-current
!git symbolic-ref --short refs/remotes/origin/HEAD
```

Strip the `origin/` prefix; **never assume `main`**. Then list the docs the
change touches. The Stop hook and this skill share one detector, so an audit
covers exactly what the hook flagged:

```
!python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/audit-docs-gate.py" --list --scope branch
```

`--scope working` for uncommitted only, `--scope staged` for the index. Trailing
paths restrict it. Output is `path<TAB>+added/-removed`; the churn figure is
only there to help you order the work.

If `$ARGUMENTS` names a PR, use `gh pr diff <n> --name-only` instead. If nothing
comes back and no paths were given, say so and stop.

### Step 2: Read the whole file, and its siblings

The changed lines are the trigger, not the scope. Read each target in full, then
the docs beside it — for the ownership check you need to know what the other
files already claim, and for the consistency check you need their conventions.

Where a repo has an `AGENTS.md` or `CLAUDE.md` index linking into `docs/`, read
that first: it tells you what each doc is supposed to own.

### Step 3: Verify the claims

The step that cannot be skipped, and the one that takes the time. Build the list
of checkable assertions from step 2 and confirm each against the repo — `ls`,
`test -f`, `rg` for the symbol, read the `Makefile`, read the arg parser.

Group the lookups: one `rg` for six symbol names beats six calls.

Mark each claim **confirmed**, **wrong**, or **unverifiable**. Unverifiable is a
real answer — a claim about a system you cannot reach from here stays, and gets
reported as unverified.

### Step 4: Judge

One verdict per finding: **keep**, **correct**, **rewrite**, **cut**, or
**move**. Name the check that failed. Keeps are silent.

### Step 5: Apply

Make the edits, unless `--dry-run`. When a move crosses files, do both halves in
the same pass — a fact deleted from one doc and not yet written into the other
is worse than either state.

Do not touch code. If a doc is wrong because the code is wrong, say so and stop
at the doc.

### Step 6: Report

Lead with what was wrong, not what was checked:

```
Audited 3 docs (AGENTS.md, README.md, docs/04-ingest.md).

Corrected (4)
  README.md:38          `make worktree-env` — no such target; it's `make env-worktree`
  docs/04-ingest.md:12  eight state machines listed, the template defines nine
  AGENTS.md:22          links to docs/setup.md, moved to docs/01-setup.md
  ...

Moved (1)
  README.md:60-95       the refresh-pipeline walkthrough → docs/04-ingest.md,
                        README now links to it. Setup was below the fold.

Cut (2)
  AGENTS.md:44          the file tree — `ls` says it better and it was already stale

Unverified (1)
  docs/04-ingest.md:30  "Trackman posts within 30s of round completion" — can't
                        check from here, left as written.
```

## Notes

- **Doc rot is silent.** Nothing fails when a doc goes stale, which is why this
  skill weights verification over style. If time is short, do check 1 and stop.
- **`scripts/audit-docs-gate.py` runs on `Stop`** and blocks once per commit per
  session when a doc changes in the working tree, the same shape as the comment
  gate. It hands the audit to the `audit-docs` subagent, which is where the
  Haiku pin lives — so you may be reading this as that agent rather than in the
  session that made the edits. `AUDIT_DOCS_HOOK=0` disables it.
- **Which files count is the script's business** — `DOC_NAMES` and the `docs/`
  rule in the gate are the list. Markdown that nobody maintains claim by claim
  (`CHANGELOG.md`, licences) is excluded deliberately: firing on generated files
  teaches the reader to ignore the gate.
- `Skill(audit-comments)` feeds this via its check 8, but does not call it. A
  fact moved out of a comment lands in a doc, which makes that doc a touched
  file, which arms this gate on its own.
- On a repo whose `docs/` is linked from `AGENTS.md`, that index is also a
  check: a doc nothing links to is a doc nothing reads.
