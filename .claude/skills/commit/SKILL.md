---
name: commit
description: Creates git commits with gitmoji conventional format
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git symbolic-ref:*), Bash(git rebase:*), Bash(git push:*), Read, Skill(branch)
user-invocable: true
model: haiku
---

# Committing

Create commits with gitmoji conventional commit format.

## Details

### Branch Protection

**NEVER commit directly to `main` or `master`.** If on `main` or `master`, automatically invoke `Skill(branch)` to create a new branch before proceeding. Do not ask — just create the branch.

### Logical Changesets

- Each commit MUST be a logical group of related changes
- Avoid bundling unrelated changes

## Message Format

```text
<emoji> <type>(<scope>): <subject>

<body>

<footer>
```

### Bash Command Rules

- **NEVER chain commands with `&&` or `;`** — run each as a separate Bash call. Compound commands don't match granular permission patterns like `Bash(git status:*)`.
- **NEVER use command substitution `$(...)` or backticks** — these trigger security prompts. Use `git commit -m "message"` with inline strings instead.

### Message Rules

- Commit messages MUST follow this format
- Commit messages MUST be consolidated into one message if retroactively amending

### Components

| Component | Required | Description                                                     |
| --------- | -------- | --------------------------------------------------------------- |
| emoji     | Yes      | Gitmoji from [gitmoji.json](gitmoji.json)                       |
| type      | Yes      | feat, fix, refactor, chore, docs, test, style, perf, ci, revert |
| scope     | No       | Module/component name (e.g., auth, api, ui)                     |
| subject   | Yes      | Imperative, lowercase, no period, <=72 chars                    |
| body      | No       | What and why (not how)                                          |
| footer    | Yes      | `Co-Authored-By: Claude <noreply@anthropic.com>`                |

### Gitmoji Reference

Primary source: [gitmoji.json](gitmoji.json) - always use this file first.

Only fetch from <https://gitmoji.dev/api/gitmojis> if:

- An appropriate emoji isn't found in the local file
- The user explicitly requests an update

Ask the user for context to select the best emoji if needed.

### Selection Criteria

1. Identify the primary purpose of the change
2. Choose the most specific matching emoji from [gitmoji.json](gitmoji.json)
3. Use one emoji per commit
4. Prioritize by impact: breaking changes > features > fixes > refactoring

## Workflow

1. Check branch: `git symbolic-ref --short HEAD` — if on `main`/`master`, run `Skill(branch)` first
2. Review changes: `git status` then `git diff` (as separate commands)
3. Analyze changes: `Skill(structuring-changesets)`
4. Stage each group: `git add <files>`
5. Commit with gitmoji format
6. Push: `git push -u origin <branch-name>` (auto-push, no confirmation needed)
7. Verify: `git log --oneline -5`

## Examples

### Single-line format - simple changes

```text
✨ feat(auth): change OAuth2 redirect URI to constant

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Extended format for complex changes

```text
✨ feat(auth): add OAuth2 login support

Implement Google and GitHub OAuth2 providers for user authentication.

- Implemented OAuth2 flow with token exchange
- Updated user model to store OAuth2 tokens

Co-Authored-By: Claude <noreply@anthropic.com>
```
