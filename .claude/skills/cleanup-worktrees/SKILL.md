---
name: cleanup-worktrees
description: Prune git worktrees whose branches have been merged or whose remote tracking branch is gone (e.g. after a PR merge with auto-delete). Use when the user wants to tidy stale worktrees, says "cleanup worktrees", "prune worktrees", "remove old worktrees", or similar.
allowed-tools: Bash(git worktree:*), Bash(git fetch:*), Bash(git branch:*), Bash(git status:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(git for-each-ref:*), Bash(basename:*)
user-invocable: true
model: haiku
---

# Cleanup Worktrees

Remove worktrees whose work is done — branch merged into `main` or remote tracking branch gone (typical after a PR is merged and the head branch is auto-deleted on GitHub).

## Behavior

- **Never delete dirty worktrees.** If a worktree has uncommitted changes, skip it and report.
- **Never delete the main worktree** (the one checked out on `main`/`master`).
- **Show before removing.** Print the plan, then execute.
- **Honour `$ARGUMENTS`:** if it contains `--dry-run`, list candidates but do not remove anything.

## Workflow

### Step 1: Fetch with prune

This drops remote-tracking refs for branches that have been deleted on the remote (e.g. after a merged PR with auto-delete).

```
!git fetch --prune origin
```

### Step 2: Determine main branch

```
!git symbolic-ref --short refs/remotes/origin/HEAD
```

Strip the `origin/` prefix. If that fails, default to `main`.

### Step 3: List worktrees

```
!git worktree list --porcelain
```

Parse the porcelain output. Each worktree block has `worktree <path>`, `HEAD <sha>`, and either `branch refs/heads/<name>` or `detached`.

### Step 4: Compute merged branches

```
!git branch --merged <main-branch>
```

This is the set of local branches fully merged into `main`.

### Step 5: Classify each worktree

For each worktree (skipping the primary one — the one whose path is the repo root, which is typically on `<main-branch>`):

- **Skip** if branch == `<main-branch>` or detached HEAD.
- **Skip + warn** if `git -C <path> status --porcelain` is non-empty (dirty).
- **Candidate (merged)** if the branch is in the merged list.
- **Candidate (remote gone)** if `git rev-parse --verify --quiet refs/remotes/origin/<branch>` fails AND the branch had an upstream previously. Detect "had an upstream" by checking `git for-each-ref --format='%(upstream)' refs/heads/<branch>` returns a non-empty value pointing at `refs/remotes/origin/<branch>`.
- **Keep** otherwise (still in flight).

### Step 6: Report the plan

Print a short table:

```
Will remove:
  ../repo-feat-foo        feat/foo        (merged into main)
  ../repo-fix-bar         fix/bar         (remote branch gone)

Skipping (dirty, has uncommitted changes):
  ../repo-wip-thing       feat/wip-thing

Keeping:
  ../repo-active          feat/active     (still in flight)
```

If `$ARGUMENTS` contains `--dry-run`, stop here.

### Step 7: Remove

For each candidate:

```
!git worktree remove <path>
!git branch -D <branch>
```

Then:

```
!git worktree prune
```

### Step 8: Final report

One or two lines: how many worktrees removed, how many skipped (dirty), how many kept. Mention the dry-run flag if anything was skipped due to dirtiness.

## Notes

- Use `git branch -D` (capital D) for the local branch delete since the upstream is often gone, which makes `-d` refuse.
- Never pass `--force` to `git worktree remove`. If it refuses (e.g. submodule weirdness), surface the error to the user instead of forcing.
- The "remote gone" check requires the branch to have had an upstream — otherwise a brand-new local-only worktree would be flagged as cleanable.

## Examples

User runs `/cleanup-worktrees`:

1. Fetch with prune
2. Find 2 merged worktrees and 1 with a deleted remote → remove all 3 and their branches
3. Skip 1 dirty worktree with a warning
4. Report: "Removed 3 worktrees (2 merged, 1 remote-gone). Skipped 1 dirty: ../repo-wip-thing."

User runs `/cleanup-worktrees --dry-run`:

1. Same analysis
2. Print the plan but do nothing
3. Report: "Dry run — would remove 3 worktrees, skip 1 dirty."
