# Global Standards

These defaults apply to every project. If a repo's own `AGENTS.md` says
something different, follow the repo.

## Worktrees

- Work in a git worktree rather than the main checkout wherever you can
  (`/create-worktree`). Worktrees go under `<repo>/.worktrees/`, never in
  sibling folders.
- Whatever a worktree runs has to be isolated to that worktree: its own Compose
  project and its own ports. Don't hardcode a port.
- Tear down a worktree's Docker stack (`make docker-clean`) before you remove
  the worktree. Otherwise its containers, images and volumes are orphaned.

## Docker

- Containerise wherever you can. Run, test and debug through Docker Compose.
  Use the host only for editor tooling and git hooks, not as a second way to run
  the app.
- Preserve layer caching: install dependencies before copying source. Treat a
  cache regression as a bug.

## Make

- The `Makefile` is the entry point for every task. If a target exists, use it
  instead of calling `uv`, `npm` or `docker compose` directly. A new command
  gets a new target.
- Stick to the usual target names: `install`, `install-dev`, `format`,
  `format-check`, `lint`, `typecheck`, `deadcode`, `test`, `pre-commit`,
  `check` and `clean`, plus `docker-dev`, `docker-test` and `docker-clean`.
  `check` runs every check and is what CI runs. In a monorepo, the root
  `Makefile` runs each target in every sub-project with `$(MAKE) -C`.

## Tools

A project needs a tool for each of these jobs: dependency management with a
lockfile and a pinned runtime version, a formatter, a linter, a type checker, a
dead-code finder and a test runner. Choose whatever is standard and fast for the
stack. An existing repo keeps the tools it already has.

As a starting point, not a rule: `uv`, Black, Ruff, ty, vulture and pytest for
Python, and Prettier, oxlint, `tsc` and knip for TypeScript.

Run each tool through its `make` target, not directly.

## Git hooks

- Every project has a pre-commit hook that runs formatting, linting,
  type-checking and dead-code checks. `make install-git-hooks` installs it, and
  `make init` runs that for you.
- Keep the checks in the `Makefile`'s `pre-commit` target.
  `.pre-commit-config.yaml` only routes to `make pre-commit`, and in a monorepo
  it routes by path to `make -C <project> pre-commit`.
- Never bypass the hook with `--no-verify`. Don't rely on it as your first
  signal either: run the checks yourself before you call a change done.

## Pull requests

- Open or update a PR with `/ship`, not by hand. It audits the comments and docs
  the branch touched, commits, pushes and writes the PR in one pass, so the
  audit's fixes end up in the PR's own commit.
- For only part of that flow, use `/commit` or `/pull-request`.

## GitHub

- Use the `gh` CLI for everything on GitHub: PRs, reviews, checks and Actions.
  To see why CI failed, use `gh run list`, `gh run view --log-failed` and
  `gh run watch`. To start a workflow, use `gh workflow run`. Don't scrape the
  web UI.
- CI calls `make check` rather than repeating the steps in YAML. For building,
  pushing and deploying, use the shared composite actions in
  `Rhodri-Morgan/github-workflows` instead of copying their steps.

## Docs

- `AGENTS.md` holds the rules for agents: conventions, targets and traps.
  It loads on every turn, so keep it short and link out to `docs/`.
  `CLAUDE.md` only points at `AGENTS.md`.
- `README.md` is for people: what the project is and how to start it.
- `docs/` gives the macro picture: architecture, local development,
  configuration and deployment. Number the files (`1_architecture.md`) and
  give each one a row in the `AGENTS.md` index. Write only stable concepts
  there. Volatile details such as command names and thresholds belong in
  `AGENTS.md` or the source.
- Docs live next to what they describe. A sub-project owns its own `docs/`.
- Update a doc in the same change that makes it stale.

## Comments

A comment has to earn its place. The default is no comment.

- Keep a comment only for something the reader can't get from the code, the
  upstream library or docs one search away. That means a constraint from
  another system, a workaround for someone else's bug, a business rule, or why
  a non-obvious decision was made.
- Cut comments that restate the code, repeat what a name already says, or
  narrate the change ("added X", "now uses Y").
- Facts about how the system fits together go in `docs/`, not in comments.
- Match the comment style of the surrounding files, and keep each comment as
  short as the fact allows.

## Verbosity

Less is more, in code and in prose. Make the smallest change that works and
skip speculative abstractions. In docs, commit messages and PR text, say each
thing once and briefly.
