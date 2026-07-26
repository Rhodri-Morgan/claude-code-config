---
name: cursor
description: Open the current worktree, the main repo, or a named worktree in Cursor. Use when the user says "/cursor", "open in cursor", "open this in my editor", "open that worktree", or similar.
allowed-tools: Bash(cursor:*), Bash(git rev-parse:*), Bash(git worktree:*), Bash(git symbolic-ref:*), Bash(pwd), Bash(basename:*), Bash(command:*), Bash(test:*)
user-invocable: true
model: haiku
---

# Open in Cursor

Launch Cursor on a directory — by default the worktree you are currently working in, not the main repo.

## Behavior

- **Current worktree wins.** With no arguments, open `git rev-parse --show-toplevel`. Inside a worktree that resolves to the worktree, which is the point — you get the checkout you are actually working in.
- **Not a git repo** → open the current directory.
- **Never ask for confirmation** — resolve the target and launch.
- **Reuse, don't proliferate.** Plain `cursor <path>` focuses an existing window for that folder. Only pass `-n` when the user explicitly asks for a new window.

## Argument Resolution

Resolve `$ARGUMENTS` in this order, first match wins:

1. **Empty** → current worktree root (see Step 1).
2. **`main`, `root`, or `primary`** → the main worktree: the first `worktree` entry in `git worktree list --porcelain`.
3. **An existing path** (relative or absolute) → that path, as given.
4. **A branch name or worktree slug** → match against `git worktree list --porcelain`. Compare the argument against both the `branch refs/heads/<name>` value and the basename of each worktree path, accepting a `/` → `-` slug match so `feat/oauth` finds `.worktrees/feat-oauth`. Unique substring matches are fine.
5. **No match** → stop and report. List the available worktrees rather than guessing or creating anything.

`-n` / `--new` anywhere in `$ARGUMENTS` means open a new window; strip it before resolving the target.

## Workflow

### Step 1: Resolve the target

```
!git rev-parse --show-toplevel 2>/dev/null || pwd
```

If `$ARGUMENTS` is non-empty, also list the worktrees to resolve against:

```
!git worktree list --porcelain
```

### Step 2: Check Cursor is installed

```
!command -v cursor
```

If this returns nothing, stop and tell the user to install the `cursor` shell command via Cursor's **Shell Command: Install 'cursor' command in PATH** from the command palette. Do not fall back to another editor.

### Step 3: Launch

```
!cursor "<resolved-path>"
```

With `-n` requested:

```
!cursor -n "<resolved-path>"
```

The command returns immediately — Cursor launches detached. A silent exit is success.

### Step 4: Report

One line: what was opened and which branch it is on. For example:

```
Opened .worktrees/feat-oauth (feat/oauth) in Cursor.
```

## Examples

`/cursor` from inside `~/repos/mulligan-rest-api/.worktrees/feat-oauth`
→ opens that worktree, not `~/repos/mulligan-rest-api`.

`/cursor main`
→ opens the primary checkout even though you invoked it from a worktree.

`/cursor feat/oauth`
→ resolves the slug and opens `.worktrees/feat-oauth`.

`/cursor ../some-other-repo`
→ path exists, opens it directly.

`/cursor -n`
→ current worktree in a new window.
