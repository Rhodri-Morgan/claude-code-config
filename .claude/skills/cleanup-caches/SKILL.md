---
name: cleanup-caches
description: Reclaim disk space from build and tool caches — Python bytecode, pytest/ruff/mypy, uv/pip/npm caches, and optionally .venv, node_modules and .terraform provider downloads. Use when the user wants to clear caches, says "clean caches", "clear python cache", "clear terraform cache", "my disk is full", or similar.
allowed-tools: Bash(find:*), Bash(du:*), Bash(df:*), Bash(ls:*), Bash(git worktree:*), Bash(git rev-parse:*), Bash(uv cache:*), Bash(pip cache:*), Bash(npm cache:*), Bash(echo:*), Bash(printf:*), Bash(sort:*), Bash(awk:*), Bash(head:*), Bash(wc:*), Bash(command:*)
user-invocable: true
model: sonnet
---

# Cleanup Caches

Free disk space by removing caches that a tool will rebuild on its own: Python
bytecode and test/lint caches, the shared uv/pip/npm download caches, and — on
request — the per-project `.venv`, `node_modules` and `.terraform` directories.

## Behavior

- **Report before removing.** Size each group first, print the plan, then act.
- **Tiered.** Tier 1 costs nothing but CPU on the next run and goes unprompted.
  Tier 2 costs a network round trip (re-download, re-init) and needs
  confirmation.
- **Scope is the repo and its worktrees**, not the whole disk. Every worktree
  carries its own `.venv` / `node_modules` / `.terraform`, which is why the
  totals get large.
- **Honour `$ARGUMENTS`:**
  - `--dry-run` — report the plan, remove nothing.
  - `--deep` — include tier 2.
  - `--global` — include the shared uv/pip/npm caches in tier 2.
  - `--yes` — skip the tier 2 confirmation. Never assume it.
  - a path — clean that tree instead of the current repo.

## Tiers

| Tier | What | Cost of removing it | Runs by default |
| ---- | ---- | ------------------- | --------------- |
| 1 | `__pycache__`, `*.pyc`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.turbo`, `uv cache prune` | A slower first run | Yes |
| 2 | `.venv`, `node_modules`, `.terraform` | Re-download on next `uv sync` / `npm ci` / `terraform init` | `--deep` |
| 2 | `uv cache clean`, `pip cache purge`, `npm cache clean --force` | Re-download for *every* project on this machine | `--global` |

## Workflow

### Step 1: Establish the scope

```
!git rev-parse --show-toplevel
!git worktree list --porcelain
```

Clean the repo root and every worktree path it lists. Outside a git repo, or
when `$ARGUMENTS` names a path, use that directory.

### Step 2: Size each group

```
!find <root> -type d -name __pycache__ -prune -print0 | xargs -0 du -sch 2>/dev/null | tail -1
```

Repeat per group. `.venv`, `node_modules` and `.terraform` are usually two
orders of magnitude larger than the tier 1 groups — size them separately so the
plan shows where the space actually is.

### Step 3: Print the plan

```
Caches under claude-code-config (4 worktrees): 3.1 GB

Tier 1 — regenerable, running now:
  __pycache__ (212 dirs)        84 MB
  .pytest_cache (6)             12 MB
  .ruff_cache / .mypy_cache     31 MB
  uv cache prune (unreachable)  ~200 MB

Tier 2 — needs a re-download (--deep):
  .venv (4)                     1.2 GB
  node_modules (2)              980 MB
  .terraform (3)                610 MB   (terraform init before the next plan)
```

If `$ARGUMENTS` contains `--dry-run`, stop here.

### Step 4: Tier 1

Runs without asking:

```
!find <root> -type d -name __pycache__ -prune -exec rm -rf {} +
!find <root> -type f -name '*.pyc' -delete
!find <root> -type d \( -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name .turbo \) -prune -exec rm -rf {} +
!uv cache prune
```

`-prune` stops `find` descending into a directory it is about to delete, which
is what keeps `__pycache__` nested inside `.venv` from being walked twice.

`uv cache prune` removes only unreachable entries — wheels no environment on
this machine still points at. It is not the same as `uv cache clean`, which is
tier 2.

### Step 5: Tier 2 — per-project directories

Only with `--deep`, and only after confirmation naming the totals.

```
!find <root> -maxdepth 3 -type d \( -name .venv -o -name node_modules -o -name .terraform \) -prune -exec rm -rf {} +
```

`-maxdepth 3` keeps this to the project's own directories rather than the
copies vendored inside `node_modules`, which go with their parent anyway.

Never touch `.terraform.lock.hcl` — it is committed, and deleting it changes
which provider versions the next `init` resolves.

### Step 6: Tier 2 — shared caches

Only with `--global`, and only after confirmation. These are machine-wide: the
next `uv sync` in *any* repo re-downloads.

```
!uv cache clean
!pip cache purge
!npm cache clean --force
```

Skip any whose tool is not installed rather than reporting a failure.

### Step 7: Report

Two or three lines — reclaimed total, what went, what was left:

```
Reclaimed 3.1 GB.
Removed 212 __pycache__, 6 pytest caches, 4 .venv, 3 .terraform.
Kept node_modules (--deep only covers what was asked) and the shared uv cache.
```

Name any directory that now needs a re-init before it will build:
`terraform init` for each `.terraform` removed, `uv sync` for each `.venv`.

## Notes

- **Never delete `~/.terraform.d/plugin-cache`.** It is what makes re-`init`
  cheap after a `.terraform` removal — providers come from there instead of the
  registry. The destructive-command guard protects it anyway.
- **`.next`, `dist` and `build` are output, not cache.** They are cheap to
  rebuild but a running dev server will break mid-flight, so they are out of
  scope here.
- A `.venv` removed from a worktree takes its direnv state with it — the next
  `cd` re-renders `.env` from SSM, which needs AWS credentials to be live.
- `find ... -exec rm -rf {} +` is not seen by the destructive-command guard,
  which only inspects the leading command word. The `-prune` and `-maxdepth`
  bounds above are therefore the only thing keeping the deletion scoped — do not
  relax them.

## Examples

`/cleanup-caches`

1. Size every group across the repo and its worktrees
2. Run tier 1 → ~300 MB back
3. Report tier 2 with sizes and stop

`/cleanup-caches --deep --yes`

1. Tier 1 unprompted
2. Remove `.venv`, `node_modules` and `.terraform` across all worktrees
3. Report which directories need `uv sync` / `terraform init`

`/cleanup-caches --dry-run`

1. Report the plan across both tiers
2. Remove nothing
