---
name: pull-request
description: Create a pull request with AI-generated description
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git rev-parse:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh pr edit:*), Read, Glob
user-invocable: true
---

# Create Pull Request

Open or update a pull request for the current branch, with a description a reviewer can actually read.

## Writing the description

**The reader is a colleague who has not been following along.** They want to know what problem this solves and what they are being asked to approve. They can read the diff themselves — what they cannot get from the diff is why, what was considered, and what might bite.

Write it the way you would explain the branch to someone at their desk: what was wrong, what you did, what to watch for. Then stop.

### The test for every line

**Could the reader get this from the diff?** If yes, cut it. A bullet that says "adds `install-yes` target to Makefile" is the diff in prose. A bullet that says "`install.sh` reads its confirmation from stdin, so an agent shell could never get through the make front door" is the reason the diff exists, and only you know it.

The same test the repo applies to code comments applies here.

### Length

| Section | Target |
| ------- | ------ |
| Summary | 1–3 sentences |
| Changes | 3–7 bullets, one line each where possible |
| Testing | What you ran and what it showed |

A large PR earns a longer **Changes** section, not a longer everything. If a section runs past its target, the usual cause is narration that belongs nowhere — cut it rather than reorganising it.

### What to include

- **The problem first.** Open with what was wrong or missing. "X silently did nothing when Y" beats "This PR adds a check for Y".
- **Decisions and their reasons.** Anything where you picked one option over another and a reviewer might wonder why.
- **Anything surprising.** A non-obvious failure mode, a constraint from another system, a workaround for someone else's bug. This is the highest-value content in the whole description.
- **Anything with a blast radius.** Behaviour changes, deletions, permission or config changes, things that alter what runs on someone's machine.
- **What you actually ran**, and what it showed. Real numbers and real output beat "tested locally".

### What to leave out

- **File-by-file inventories.** The diff does this better.
- **Restating the title** as the first line of the Summary.
- **Section headers with nothing under them.** If a section has no content, say so in a few words — "Not tested; docs only" — and move on.
- **Padding**: "This PR aims to…", "In order to improve…", "Various improvements to…".
- **Every commit as a bullet.** Group by intent. Two commits touching the same idea are one bullet; one commit doing three things is three.
- **Bold on every noun.** Emphasis that is everywhere emphasises nothing.

### Shape

Prose for the Summary. Bullets for Changes. A table only when there are genuinely several things to compare — a tier list, a before/after, a matrix of flags. Tables of two rows are worse than two sentences.

## Title format

Conventional commit format with an emoji from [gitmoji.json](../../shared/gitmoji.json), using the actual character rather than `:code:`:

```
<emoji>(<scope>): <short description>
```

Examples: `✨(auth): Add OAuth2 login flow`, `🐛(api): Fix null pointer in user endpoint`, `📝(docs): Update README with setup instructions`.

## Workflow

### Step 1: Resolve the branch and the base

```
!git branch --show-current
```

Stop if this is the default branch — there is nothing to open a PR from.

**Never assume the base is `main`.** Resolve it:

```
!git symbolic-ref --short refs/remotes/origin/HEAD
```

Strip the `origin/` prefix. If that fails, fall back to whichever of `main` or `master` exists. Use the resolved name everywhere below, including `--base`.

### Step 2: Read the repo's template

```
!ls .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md
```

If one exists, its section headers win over anything in this skill — match them exactly. If none exists, use Summary / Changes / Testing.

The template's HTML comments are guidance for the author. Strip them from the body you submit; do not answer them inline.

### Step 3: Check for an existing PR

```
!gh pr list --head <branch> --json number,title,url --jq '.[0] // empty'
```

### Step 4: Read the whole branch

```
!git log --oneline <base>..HEAD
!git diff --stat <base>...HEAD
!git diff <base>...HEAD
```

**Always `<base>...HEAD`, never a diff between two commits on the branch.** The description covers everything the merge would land, whether this is a new PR or the fifth update to an existing one. Updating a PR rewrites the whole description — it is not an changelog appended to.

Use `git log` to understand the sequence of thinking. Use the diff to decide what to write. The commits are not the outline.

### Step 5: Push if needed

```
!git push -u origin <branch>
```

### Step 6: Create or update

New — always a draft:

```
!gh pr create --title "TITLE" --body "BODY" --base <base> --draft
```

Existing:

```
!gh pr edit <number> --title "TITLE" --body "BODY"
```

Do not ask for confirmation at any point. Report the URL when done.

## Example

A branch that added a Docker cleanup skill and a make target.

**Too long — a diff in prose:**

> ## Summary
> This PR adds a new `cleanup-docker` skill to the repository in order to help
> with reclaiming Docker disk space, along with various documentation updates.
>
> ## Changes
> - Added `.claude/skills/cleanup-docker/SKILL.md` with 220 lines
> - Added `Skill(cleanup-docker)` to the allow list in `settings.json`
> - Added `install-yes` target to the `Makefile`
> - Updated `README.md` with a new row in the target table
> - Updated `AGENTS.md` with a new row in the target table

Every bullet is visible in the diff. Nothing says why any of it happened.

**Right:**

> ## Summary
> Docker was holding 33.9 GB on this machine, most of it build cache and images
> pinned by compose stacks whose worktree had been deleted months ago.
> `docker system prune -a` is the usual answer and is wrong here: local stacks
> are per-worktree and several run at once, so a stopped stack is a checkout you
> may resume, not dead work.
>
> ## Changes
> - Four tiers, safest first. Only tier 1 runs unprompted; volumes always need
>   `--volumes` and an explicit confirmation, since local DB data lives in them.
> - Tier 1 spares every compose project via `label!=com.docker.compose.project`,
>   so a stopped stack survives. Only stacks whose compose file is gone are torn
>   down.
> - Prune order matters: removing an image orphans the build-cache records that
>   made it, so a builder-first pass leaves most of the cache behind — 2.0 GB on
>   the first pass, 10.3 GB on the pass straight after the image prune.
> - Container IDs go through `xargs`. zsh does not word-split unquoted
>   expansions, so `docker stop $ids` sends them as one argument, the daemon
>   rejects it, and `container prune` then reports success against a stack that
>   is still running.
> - `make install-yes`, because `install.sh` reads its confirmation from stdin
>   and an agent shell could not get through the make front door without it.
>
> ## Testing
> Ran end to end: 33.9 GB → 4.2 GB, ten dead stacks removed, six live stacks
> verified still up and healthy. Both bugs above were caught by that run.

Same branch, and shorter — but a reviewer now knows what to look at.
