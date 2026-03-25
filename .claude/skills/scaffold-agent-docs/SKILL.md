---
name: scaffold-agent-docs
description: Use when a repository is missing AGENTS.md or CLAUDE.md, when setting up a new repo, or when the user asks to scaffold agent documentation
user-invocable: true
---

# Scaffold Agent Docs

Ensure a repository has properly structured AGENTS.md and CLAUDE.md files.

## Behavior

1. **Detect repo name** from git remote origin URL (fallback: current directory name)
2. **Check** for existing AGENTS.md and CLAUDE.md in the repo root
3. **Create missing files** — never overwrite existing ones
4. **Report** what was created or what already exists

## File Templates

### CLAUDE.md

```markdown
# <repo-name> — Claude Code

See [AGENTS.md](AGENTS.md).
```

### AGENTS.md

```markdown
# <repo-name> — Agent Instructions
```

## Rules

- Derive `<repo-name>` from the git remote origin URL (strip `.git` suffix, take last path segment). If no remote, use the directory name.
- If a file already exists, do NOT overwrite it. Report that it already exists.
- If both files already exist, report that and take no action.
- Create files at the repository root (where `.git/` lives), not the current working directory if different.
