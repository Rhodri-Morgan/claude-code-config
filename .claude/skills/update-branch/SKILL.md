---
name: update-branch
description: Rebase the current feature branch onto the latest main, resolving conflicts. Use when the user wants to sync their branch with main, says "update branch", "rebase on main", "pull in main", "sync with main", "update from main", or similar. Fetches origin, fast-forwards local main, rebases the feature branch onto it, and attempts to resolve any conflicts inline.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git fetch:*), Bash(git checkout:*), Bash(git switch:*), Bash(git pull:*), Bash(git rebase:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git log:*), Bash(git add:*), Bash(git stash:*), Bash(git rev-parse:*), Bash(git ls-files:*), Read, Edit
user-invocable: true
model: haiku
---

# Update Branch

Rebase the current feature branch onto the latest `main`, auto-resolving conflicts where possible.

## Behavior

- **Rebase, not merge.** Keeps history linear.
- **Auto-stash** any uncommitted changes before the rebase; pop after success.
- **Resolve conflicts inline.** Read each conflicted file, edit out the conflict markers, `git add`, `git rebase --continue`. Repeat until clean.
- **Never ask for confirmation** — execute the full flow.
- **Never force-push.** This skill only updates the local branch. Pushing is the user's call.

## Workflow

### Step 1: Guardrails

```
!git symbolic-ref --short HEAD
```

If on `main` or `master`, stop — there's nothing to rebase. Report back and exit.

### Step 2: Stash if dirty

```
!git status --short
```

If there's output, stash including untracked:

```
!git stash push -u -m "update-branch: auto-stash before rebase"
```

Remember whether a stash was created so you can pop it in Step 6.

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

If `main` can't be fast-forwarded, stop and report — don't force anything.

### Step 4: Rebase the feature branch

```
!git switch <feature-branch>
```

```
!git rebase main
```

### Step 5: Resolve conflicts (loop until clean)

If `git rebase` exits non-zero with conflicts:

1. Run `git status` to list conflicted files.
2. For each conflicted file:
   - `Read` the file.
   - Use `Edit` to remove the `<<<<<<<`, `=======`, `>>>>>>>` markers and produce the correct merged content. Use your understanding of both sides to pick the right resolution — do not blindly keep one side.
   - Run `git add <file>`.
3. When all files are staged, run `git rebase --continue`.
4. If more conflicts appear on the next commit, repeat from step 1.
5. If a conflict is genuinely ambiguous (e.g. two semantically incompatible changes to the same logic), stop, run `git rebase --abort`, and report to the user which file and which hunk was ambiguous. Restore any stash from Step 2.

### Step 6: Pop the stash

If a stash was created in Step 2:

```
!git stash pop
```

If popping the stash produces conflicts, report them to the user — don't try to auto-resolve stash-pop conflicts (they indicate the rebase changed something the stashed edits also touched, which is worth human attention).

### Step 7: Report

Tell the user:

- Rebase result (success / aborted)
- How many commits were replayed
- Whether conflicts were resolved, and which files
- Whether a stash was popped cleanly
- Reminder: push will need `--force-with-lease` if the branch was previously pushed (do NOT do this automatically)

Keep it to 3–6 lines.

## Conflict-resolution rules

- Preserve intent from both sides when possible. If one side renames a symbol and the other adds a call site, keep the rename AND update the new call site.
- For lockfiles (`package-lock.json`, `uv.lock`, `Cargo.lock`, etc.), prefer regenerating from the manifest rather than hand-editing: keep `main`'s version and tell the user to re-run the package manager.
- For generated files, take `main`'s version and note that regeneration may be needed.
- Never leave conflict markers in a "resolved" file.

## Examples

Clean rebase, no conflicts:

1. Stash 2 modified files
2. `main` fast-forwarded (3 new commits)
3. Rebased branch `feature/auth` (4 commits replayed cleanly)
4. Stash popped
5. Reported: success, no conflicts, reminder about `--force-with-lease` if already pushed

Rebase with one conflict:

1. No stash needed
2. `main` updated
3. Rebase hits conflict in `src/api/user.ts`
4. Read file, resolve markers keeping both the rename from main and the new field from feature
5. `git add src/api/user.ts`, `git rebase --continue`
6. Rest of rebase proceeds cleanly
7. Reported: success, 1 conflict resolved in `src/api/user.ts`

Ambiguous conflict:

1. Rebase hits conflict where both sides rewrote the same function differently
2. `git rebase --abort`
3. Restore stash
4. Reported: aborted, ambiguous conflict in `<file>:<function>`, user needs to decide
