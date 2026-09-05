---
name: cleanup
description: Run every cleanup in one pass — prune merged worktrees, clear build and tool caches, then reclaim Docker space. Use when the user wants a general tidy-up, says "clean up", "free some space", "my disk is full", "run all the cleanups", or similar.
allowed-tools: Skill(cleanup-worktrees), Skill(cleanup-caches), Skill(cleanup-docker), Bash(df:*)
user-invocable: true
model: haiku
---

# Cleanup

Run the three cleanup skills back to back and report one combined total.

## Workflow

Run in this order — each stage creates work for the next:

1. **`Skill(cleanup-worktrees)`** — removing a worktree takes its `.venv`,
   `node_modules` and `.terraform` with it, and orphans its compose stack.
2. **`Skill(cleanup-caches)`** — what survived step 1 is still-live work, so
   this only sizes caches that are actually worth reporting.
3. **`Skill(cleanup-docker)`** — the stacks orphaned by step 1 now show up as
   tier 2 candidates.

Run them one at a time, not concurrently: each stage's plan depends on what the
previous one removed.

## Rules

- Pass `$ARGUMENTS` through to every sub-skill. They share `--dry-run` and
  `--yes`; each ignores flags it does not recognise. `--machine` reaches
  `cleanup-caches` alone, and widens it past this repo to the home-directory
  caches (simulators, AVDs, DerivedData, package-manager caches).
- Relay each sub-skill's own report — do not re-derive its numbers.
- A sub-skill that cannot run (no Docker daemon, not a git repo) is a one-line
  note, not a failure. Continue to the next stage.
- Finish with a combined total and one line naming anything that now needs a
  re-init before it will build.

## Examples

`/cleanup`

1. Prune merged worktrees, clear tier 1 caches, prune tier 1 Docker
2. Report each stage's offer of the deeper tiers, in one list

`/cleanup --dry-run`

1. Every stage reports its plan, nothing is removed

`/cleanup --deep --all --yes`

1. Full pass — merged worktrees, `.venv` / `node_modules` / `.terraform`,
   orphaned stacks and unused images. Volumes still need `--volumes`.
