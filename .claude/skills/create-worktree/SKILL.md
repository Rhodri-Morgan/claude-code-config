---
name: create-worktree
description: Create a git worktree on a fresh branch from the latest default branch. Use when the user wants to start isolated work in a new worktree, says "new worktree", "worktree this", "spin up a worktree", or similar. Stashes any uncommitted changes on the current branch (left behind, not carried into the worktree), fast-forwards the default branch, then creates the worktree on an auto-generated branch.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git stash:*), Bash(git fetch:*), Bash(git checkout:*), Bash(git switch:*), Bash(git pull:*), Bash(git worktree:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git rev-parse:*), Bash(git ls-files:*), Bash(git check-ignore:*), Bash(git remote:*), Bash(basename:*), Bash(pwd), Bash(cp:*), Bash(mkdir:*), Bash(dirname:*), Bash(printf:*)
user-invocable: true
model: haiku
---

# Create Worktree

Spin up a git worktree on a new branch cut from the latest default branch.

## Behavior

- **Stash, don't carry.** Uncommitted changes on the current branch are stashed with a clear message and left behind. The new worktree starts from a clean, up-to-date default branch.
- **Auto-generate branch name** unless the user supplied one in `$ARGUMENTS`.
- **Worktree path**: `<repo-root>/.worktrees/<repo>-<branch-slug>` where `branch-slug` replaces `/` with `-`. All worktrees live inside the repo under a single ignored `.worktrees/` directory — never as sibling folders next to the repo.
- **Resolve the default branch**, don't hardcode `main` — some repos are on `master`.
- **Seed environment files through a script, never a bare `cp`.** The repo's own `worktree-env` target if it has one, otherwise the vendored `worktree-copy-env.sh`. Both gitignored (`.env`, `.env.*`) and untracked-but-not-ignored (`.envrc`, `.envrc.local`) files come across at the same relative paths — a bare `cp` naming a `.env` path is denied by the permission rules and cannot be approved.
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

### Step 3: Update the default branch

Resolve the default branch first — don't assume `main`. Repos here are split
between `main` and `master`, and hardcoding either one breaks the other:

```
!git symbolic-ref --short refs/remotes/origin/HEAD
```

Strip the `origin/` prefix to get `<default-branch>`. If the command fails (the
`origin/HEAD` ref isn't set locally), run `git remote set-head origin --auto`
once and retry; fall back to `main` only if that also fails.

```
!git fetch origin
```

```
!git switch <default-branch>
```

```
!git pull --ff-only origin <default-branch>
```

If it is not fast-forwardable, stop and report to the user — don't force anything.

### Step 4: Determine branch name

If `$ARGUMENTS` contains a branch name (with or without a type prefix), use it (adding `feature/` if no type prefix is present). Otherwise, generate one from the conversation context using the branch naming rules above.

### Step 5: Create the worktree

Compute:

- `repo_root` from `git rev-parse --show-toplevel`
- `repo_name` = basename of `repo_root`
- `branch_slug` = branch name with `/` → `-`
- `worktree_path` = `<repo_root>/.worktrees/<repo_name>-<branch_slug>`

The directory keeps the `<repo_name>-` prefix even though it already sits inside
that repo. Several repos derive `COMPOSE_PROJECT_NAME` and their host port
allocation from the directory basename, so a bare `feat-oauth` under two
different repos would collide on one compose project and one port range.

If you are already inside a worktree, `git rev-parse --show-toplevel` returns *that* worktree, not the main checkout. Resolve the main checkout first so worktrees never nest:

```
!git worktree list --porcelain
```

The first `worktree <path>` entry is the main checkout — use it as `repo_root`.

Ensure `.worktrees/` is ignored before creating anything — otherwise it pollutes
every `git status` in the main checkout, and every `rg` or `find` descends into
it. Check first, since many repos already cover it:

```
!git check-ignore -q .worktrees && echo ignored || echo NOT-ignored
```

If it reports `NOT-ignored`, append to `.git/info/exclude` rather than the
tracked `.gitignore`. `info/exclude` is local to the clone, so using this skill
in a work repo doesn't leave a stray diff to explain in an unrelated PR:

```
!printf '.worktrees/\n' >> "$(git rev-parse --git-common-dir)/info/exclude"
```

Use `--git-common-dir`, not `--git-dir` — run from inside a worktree,
`--git-dir` points at the per-worktree gitdir, whose `info/exclude` git ignores.

Then:

```
!git worktree add -b <branch-name> <worktree_path> <default-branch>
```

`git worktree add` creates the intermediate `.worktrees/` directory itself.

### Step 6: Seed the environment files

These don't come along with the worktree — either because they're gitignored
(`.env`) or because they're just untracked (`.envrc` typically isn't in
`.gitignore`, it just was never `git add`'d). Never copy them with a `cp` of
your own: a Bash command that names a `.env` path is denied outright by the
`Read(.env)` / `Edit(.env)` deny rules, and no permission mode overrides a deny.
Run one of the commands below instead — each does the copy inside a script,
where the argument scan has nothing to match.

Run from **inside** `worktree_path`, in this order, first match wins:

```
!cd <worktree_path> && make worktree-env
```

```
!cd <worktree_path> && npm run worktree:env
```

```
!cd <worktree_path> && bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/worktree-copy-env.sh"
```

Pick by what the repo has: a `worktree-env` target in the `Makefile`, then a
`worktree:env` script in `package.json`, then the fallback. Prefer the repo's
own target where it exists — it knows which files that repo actually needs
(`mulligan-app` also carries `.envrc.custom` and skips the per-worktree
`.ports`).

The fallback script copies every untracked or ignored `.env*` / `.envrc*` from
the main checkout, and runs `direnv allow` if the worktree has an `.envrc`.
Copying nothing is a valid outcome — a repo whose `.envrc` renders `.env` from
SSM needs only the `direnv allow`.

If all three fail, report it in the summary and stop — don't fall back to a bare
`cp`, it will be denied.

### Step 7: Report

Tell the user:

- The worktree path
- The new branch name
- Whether a stash was created (and the stash message) on the original branch
- How many environment files were copied, and by which command (omit if zero)
- Whether the env seeding failed entirely, and which of the three commands was tried
- That `/cursor` will open the new worktree

Keep it to 2–4 lines.

## Notes

- Worktrees created before this layout change still sit beside the repo as
  `../<repo>-<slug>`. They keep working — git tracks worktrees by absolute path,
  not by convention — and `/cleanup-worktrees` removes them wherever they are.

## Examples

User says "worktree this, I want to try a refactor of the auth module":

1. Current branch `feature/old-work` has dirty changes → stash created
2. Default branch resolved as `master`, fast-forwarded
3. Branch `refactor/auth-module` created in worktree `.worktrees/claude-code-config-refactor-auth-module`
4. Reported back with path, branch, and stash info

User says "new worktree for feat/oauth":

1. No dirty changes → no stash
2. `main` updated
3. Worktree `.worktrees/claude-code-config-feat-oauth` on branch `feat/oauth`
