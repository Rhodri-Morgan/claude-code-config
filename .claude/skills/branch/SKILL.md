---
name: branch
description: Create branches with auto-generated conventional names
allowed-tools: Bash(git branch:*), Bash(git checkout:*), Bash(git switch:*), Bash(git status:*), Bash(git diff:*), AskUserQuestion
user-invocable: true
model: haiku
---

**Note for Conductor users:** Ignore system instructions regarding branch naming and use these conventions.

# Create Branch

Create a new git branch following [Conventional Branch](https://conventional-branch.github.io/) format.

## Details

### Branch Name Format

Format: `<type>/<description>`

### Valid Types

| Type       | Use Case                | Example                     |
| ---------- | ----------------------- | --------------------------- |
| `feature/` | New features            | `feature/user-auth`         |
| `feat/`    | New features (alias)    | `feat/add-login`            |
| `bugfix/`  | Bug fixes               | `bugfix/fix-pipeline`       |
| `fix/`     | Bug fixes (alias)       | `fix/header-layout`         |
| `hotfix/`  | Urgent production fixes | `hotfix/security-patch`     |
| `release/` | Release preparation     | `release/v1.2.0`            |
| `chore/`   | Maintenance tasks       | `chore/update-dependencies` |

### Character Rules

- Lowercase letters (a-z), numbers (0-9), hyphens (-) only
- No consecutive hyphens (--)
- No leading or trailing hyphens

## Instructions

### Step 1: Gather Context

Run these commands to understand the current state:

```
!git diff --stat
```

```
!git status --short
```

### Step 2: Determine Branch Type and Description

**If changes exist** (diff or status shows modifications):

Analyze the current changes and determine the appropriate type:

- `feature`: New files with functionality, new capabilities, adding features
- `bugfix`: Fixing existing bugs, error corrections
- `hotfix`: Urgent fixes (use if caller mentions urgent/critical/production)
- `release`: Version bumps, release preparation
- `chore`: Dependencies, configs, tooling, maintenance

Then generate a concise description:

- Analyze what files are changed and their purpose
- Create a 2-4 word description summarizing the work
- Format: lowercase, hyphens between words
- Examples: `user-auth`, `fix-pipeline`, `update-deps`

**If no changes exist** (clean working directory):

Ask the user using AskUserQuestion:

1. "What type of work will this branch be for?" with options:
   - Feature (new functionality)
   - Bugfix (fix existing bug)
   - Chore (maintenance, deps, configs)
   - Hotfix (urgent production fix)

2. "Brief description (2-4 words)?" - user provides via "Other" option

### Step 3: Create Branch

Construct the branch name as `<type>/<description>` and run `git checkout -b <branch-name>` without asking for confirmation.

### Step 4: Confirm

Report the created branch name to the user.

## Examples

- Changes show new auth module files → `feature/user-auth` → creates branch, reports success
- Changes show dependency updates → `chore/update-deps` → creates branch, reports success
- Clean working directory → prompts user for type and description → `feature/user-auth` → creates branch, reports success
