---
name: ship
description: Use when the user invokes /ship to commit, push, and create or update a pull request in one flow
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git push:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh pr edit:*), Read, Skill(commit), Skill(pull-request), Skill(branch)
user-invocable: true
model: haiku
---

# Ship

Commit, push, and create or update a pull request in one command.

## Workflow

1. **Invoke `Skill(commit)`** — stages, commits with gitmoji conventional format, and pushes
2. **Invoke `Skill(pull-request)`** — creates a draft PR or updates an existing one

That's it. The sub-skills handle all the details including branch protection, PR formatting, and push.

## Rules

- Do NOT ask for confirmation at any step — just execute the full flow
- If `Skill(commit)` creates a branch (because you were on main), continue with that new branch
- If there are no changes to commit, skip straight to `Skill(pull-request)` (there may be unpushed commits)
- If there are no changes AND no unpushed commits AND a PR already exists, update the PR description
