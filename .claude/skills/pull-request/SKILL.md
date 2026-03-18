---
name: pull-request
description: Create a pull request with AI-generated description
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh pr edit:*), Read, Skill(branch)
user-invocable: true
---

# Create Pull Request

Create a pull request for the current branch with a comprehensive description using GitHub CLI.

## Description

Analyzes commits and changes on the current branch, generates a PR title and description following the project's template, and creates or updates a pull request.

## Details

### Prerequisites

Ensure GitHub CLI is installed and authenticated:

```bash
# Install on macOS
brew install gh

# Authenticate with GitHub
gh auth login
```

### PR Title Format

Use conventional commit format with emoji from [gitmoji.json](../commit/gitmoji.json):

- Always include an appropriate emoji at the beginning (use the actual character, not :code:)
- Format: `emoji(scope): short description`
- Examples:
  - ✨(auth): Add OAuth2 login flow
  - 🐛(api): Fix null pointer in user endpoint
  - 📝(docs): Update README with setup instructions
  - ♻️(core): Refactor database connection handling
  - 🔧(config): Update build configuration

### PR Description Structure

Follow the template at `.github/pull_request_template.md`:

- **Summary**: Brief overview of what this PR does
- **Changes**: Bullet list of key changes
- **Testing**: How the changes were tested
- **Checklist**: Code style, tests passing, docs updated

### Best Practices

- **Always create PRs as drafts** using the `--draft` flag
- Do NOT show a preview or ask for confirmation — just create the PR automatically

### Common Mistakes to Avoid

1. **Incorrect Section Headers**: Always use the exact section headers from `.github/pull_request_template.md`
2. **Missing Sections**: Include all template sections, even if marked as "N/A" or "None"
3. **Wrong Emoji Format**: Use actual emoji characters (✨) not text codes (:sparkles:)
4. **Skipping Draft**: Always create as draft
5. **Vague Descriptions**: Be specific about what changed and why
6. **Describing incremental changes instead of total changes**: When updating an existing PR, the description must reflect ALL changes on the branch compared to `main` — NOT just the changes since the last PR update or the most recent commit. Always use `git diff main...HEAD` as the source of truth

### Useful GitHub CLI Commands

```bash
# List your open pull requests
gh pr list --author "@me"

# Check PR status
gh pr status

# View a specific PR
gh pr view <PR-NUMBER>

# Convert draft PR to ready for review
gh pr ready <PR-NUMBER>

# Add reviewers to a PR
gh pr edit <PR-NUMBER> --add-reviewer username1,username2

# Merge a PR (squash by default)
gh pr merge <PR-NUMBER> --squash
```

## Instructions

### Step 1: Check Prerequisites

Run `git branch --show-current`. If on `main` or `master`, automatically invoke `Skill(branch)` to create a new branch before proceeding. Read the PR template at `.github/pull_request_template.md`.

### Step 2: Gather Branch Information

Run these commands to understand the current state:

```
!gh pr list --head "$(git branch --show-current)" --json number,title,url --jq '.[0] // empty' 2>/dev/null || echo "none"
```

```
!git log --oneline main..HEAD 2>/dev/null || git log --oneline origin/main..HEAD 2>/dev/null || echo "Could not determine commits"
```

```
!git diff --stat main...HEAD 2>/dev/null || git diff --stat origin/main...HEAD 2>/dev/null || echo "Could not determine diff"
```

### Step 3: Check for Existing PR

If a PR already exists for this branch (from Step 2), prepare to update it instead of creating a new one. **Important**: When updating an existing PR, the description must still describe ALL changes on the branch compared to `main` — not just the changes since the last update.

### Step 4: Analyze Changes

**Always compare against `main`**. Run `git diff main...HEAD` to review the full diff. This is the source of truth for the PR description — it shows everything this branch changes relative to `main`.

**Do NOT** use `git log` of recent commits or `git diff` between commits on the current branch to determine what to describe. The PR description must reflect the complete set of changes that will be merged into `main`.

### Step 5: Generate PR Content

Create a title and description following the formats in Details. Base the description entirely on the `git diff main...HEAD` output from Step 4. The description must cover all changes this branch introduces relative to `main`, regardless of whether this is a new PR or an update to an existing one.

### Step 6: Push if Needed

If the branch hasn't been pushed yet, push it first with:

```bash
git push -u origin <branch-name>
```

### Step 7: Create or Update PR

If a PR already exists:

```bash
gh pr edit <PR_NUMBER> --title "TITLE" --body "DESCRIPTION"
```

If no PR exists, create as draft:

```bash
gh pr create --title "TITLE" --body "DESCRIPTION" --base main --draft
```

## Examples

Creating a new feature PR (branch: `feature/oauth-login`):

```bash
gh pr create --title "✨(auth): Add OAuth2 login flow" --body "## Summary
Add Google and GitHub OAuth2 authentication providers.

## Changes
- Add OAuth2 configuration
- Implement login callbacks
- Add user session handling

## Testing
- Tested locally with both providers
- Added unit tests for auth flow

## Checklist
- [x] Code follows style guidelines
- [x] Tests pass
- [x] Documentation updated" --base main --draft
```

Updating an existing PR:

```bash
gh pr edit 123 --title "✨(auth): Add OAuth2 login flow" --body "Updated description..."
```
