---
name: ship
description: Use when the user invokes /ship to audit, commit, push, and create or update a pull request in one flow
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git push:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(python3:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh pr edit:*), Read, Agent(audit-comments), Agent(audit-docs), Skill(commit), Skill(pull-request), Skill(branch)
user-invocable: true
model: haiku
---

# Ship

Audit, commit, push, and create or update a pull request in one command.

## Workflow

### Step 1: Detect what needs auditing

Run both detectors. They are cheap, deterministic and print nothing when there
is nothing to audit:

```
!python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/audit-comments-gate.py" --list --scope branch
```

```
!python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/audit-docs-gate.py" --list --scope branch
```

`--scope branch` covers everything the branch adds over its base, committed and
uncommitted — so a branch built over several turns gets audited once, here,
rather than turn by turn.

### Step 2: Audit, only where a detector found something

For each detector that reported one or more lines, spawn its subagent. **Send
both Agent calls in one message** so they run concurrently:

| Detector output | Spawn |
| --------------- | ----- |
| comments > 0 | `Agent(subagent_type: "audit-comments")` |
| docs > 0 | `Agent(subagent_type: "audit-docs")` |

Give each agent no scope argument — its default is the branch, which is what
Step 1 measured.

A detector that reported `0` means **skip that agent entirely**. This is the
whole point of running the detectors first: a branch that touched no comments
and no docs costs two script runs, not two subagents.

The agents edit the working tree in place. Their fixes are therefore picked up
by Step 3 and land inside the same commit — that is why the audit runs before
the commit, not after the PR.

### Step 3: Commit and push

**Invoke `Skill(commit)`** — stages, commits with gitmoji conventional format,
and pushes.

### Step 4: Open or update the PR

**Invoke `Skill(pull-request)`** — creates a draft PR or updates an existing one.

The sub-skills handle all the details including branch protection, PR
formatting, and push.

### Step 5: Report the PR URL

Always end by printing the full PR URL on its own line, whether the PR was just
created or already existed:

```
!gh pr view --json url --jq .url
```

## Rules

- Do NOT ask for confirmation at any step — just execute the full flow
- Relay each agent's report as-is; do not re-audit its findings yourself
- If an audit agent fails or returns nothing usable, say so in one line and
  continue to the commit — a failed audit must never block the ship
- If `Skill(commit)` creates a branch (because you were on main), continue with
  that new branch
- If there are no changes to commit, skip straight to `Skill(pull-request)`
  (there may be unpushed commits) — the detectors still run, since an earlier
  commit on the branch may carry unaudited comments or docs
- If there are no changes AND no unpushed commits AND a PR already exists,
  update the PR description
- Always finish with the PR URL, even on the paths that skip the commit
