---
name: create-worktree
description: Create a git worktree on a fresh branch from latest main. Use when the user wants to start isolated work in a new worktree, says "new worktree", "worktree this", "spin up a worktree", or similar. Stashes any uncommitted changes on the current branch (left behind, not carried into the worktree), fast-forwards main, then creates the worktree on an auto-generated branch.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git stash:*), Bash(git fetch:*), Bash(git checkout:*), Bash(git switch:*), Bash(git pull:*), Bash(git worktree:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git rev-parse:*), Bash(git ls-files:*), Bash(basename:*), Bash(pwd), Bash(cp:*), Bash(mkdir:*), Bash(dirname:*)
user-invocable: true
model: haiku
---

# Create Worktree

Spin up a git worktree on a new branch cut from the latest `main`.

## Behavior

- **Stash, don't carry.** Uncommitted changes on the current branch are stashed with a clear message and left behind. The new worktree starts from a clean, up-to-date `main`.
- **Auto-generate branch name** unless the user supplied one in `$ARGUMENTS`.
- **Worktree path**: `<repo-root>/.worktrees/<branch-slug>` where `branch-slug` replaces `/` with `-`. All worktrees live inside the repo under a single gitignored `.worktrees/` directory — never as sibling folders next to the repo.
- **Copy environment files.** After creation, both gitignored (`.env`, `.env.*`) and untracked-but-not-ignored (`.envrc`, `.envrc.local`) environment files are copied from the source repo into the new worktree at the same relative paths. `.envrc` is rarely committed even when it isn't in `.gitignore`, so we look at the full "not part of the tree" set, not just the ignored slice.
- **Never ask for confirmation** — execute the full flow.

## Branch Naming

Follows the same conventions as `Skill(branch)`: `<type>/<description>` where type is one of `feature`, `feat`, `bugfix`, `fix`, `hotfix`, `release`, `chore`. Description is 2–4 lowercase hyphenated words derived from `$ARGUMENTS` or from conversation context.

## Workflow

### Step 1: Gather context

Run each as a separate Bash call:

```
!git rev-parse --show-toplevel
```

```
!git symbolic-ref --short HEAD
```

```
!git status --short
```

### Step 2: Stash if dirty

If `git status --short` produced any output, stash with a descriptive message so it's easy to find later:

```
!git stash push -u -m "create-worktree: auto-stash from <current-branch> before worktree"
```

Use `-u` so untracked files are included. Do NOT pop this stash — it stays on the original branch.

### Step 3: Update main

```
!git fetch origin
```

```
!git switch main
```

```
!git pull --ff-only origin main
```

If `main` is not fast-forwardable, stop and report to the user — don't force anything.

### Step 4: Determine branch name

If `$ARGUMENTS` contains a branch name (with or without a type prefix), use it (adding `feature/` if no type prefix is present). Otherwise, generate one from the conversation context using the branch naming rules above.

### Step 5: Create the worktree

Compute:

- `repo_root` from `git rev-parse --show-toplevel`
- `branch_slug` = branch name with `/` → `-`
- `worktree_path` = `<repo_root>/.worktrees/<branch_slug>`

If you are already inside a worktree, `git rev-parse --show-toplevel` returns *that* worktree, not the main checkout. Resolve the main checkout first so worktrees never nest:

```
!git worktree list --porcelain
```

The first `worktree <path>` entry is the main checkout — use it as `repo_root`.

Ensure `.worktrees/` is gitignored before creating anything. If the repo's `.gitignore` has no `.worktrees/` entry, add one — an un-ignored `.worktrees/` pollutes every `git status` in the main checkout.

Then:

```
!mkdir -p "<repo_root>/.worktrees"
```

```
!git worktree add -b <branch-name> <worktree_path> main
```

### Step 6: Copy environment files

These don't come along with the worktree — either because they're gitignored (`.env`) or because they're just untracked (`.envrc` typically isn't in `.gitignore`, it just was never `git add`'d). Copy both shapes from `repo_root` to the same relative path in `worktree_path`.

From inside `repo_root`, list the candidates. The union of "untracked" and "ignored" catches both shapes; tracked templates like `.env.example` are excluded automatically because they're tracked.

```
!{ git ls-files --others --exclude-standard; git ls-files --others --ignored --exclude-standard; } | sort -u | grep -v '^\.worktrees/' | grep -E '(^|/)(\.env($|\.)|\.envrc($|\.))' || true
```

The `grep -v '^\.worktrees/'` matters: `.worktrees/` is gitignored, so the ignored-file scan would otherwise walk into sibling worktrees and try to copy *their* env files into the new one.

For each path returned (call it `rel`), copy it preserving the directory structure:

```
!mkdir -p "<worktree_path>/$(dirname <rel>)" && cp "<repo_root>/<rel>" "<worktree_path>/<rel>"
```

If `cp` fails with a sandbox/permission error because the session's allowed working directories don't include the worktree, **don't retry blindly**. Report the failure in the final summary with the exact `cp` command the user should run themselves (e.g. `cp <repo_root>/<rel> <worktree_path>/<rel>`). The next Claude session, launched from the worktree, will have it as an allowed root.

If the grep finds nothing, skip silently — no env files is a valid state.

### Step 7: Report

Tell the user:

- The worktree path
- The new branch name
- Whether a stash was created (and the stash message) on the original branch
- How many environment files were copied (omit the line if zero)
- Any environment files the sandbox refused to copy, with the exact `cp` command to run manually

Keep it to 2–4 lines.

## Examples

User says "worktree this, I want to try a refactor of the auth module":

1. Current branch `feature/old-work` has dirty changes → stash created
2. `main` fast-forwarded
3. Branch `refactor/auth-module` created in worktree `.worktrees/refactor-auth-module`
4. Reported back with path, branch, and stash info

User says "new worktree for feat/oauth":

1. No dirty changes → no stash
2. `main` updated
3. Worktree `.worktrees/feat-oauth` on branch `feat/oauth`
