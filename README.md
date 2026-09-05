# Claude Code Config

Personal Claude Code configuration.

## Third-Party Skills

| Skill                       | Source                                                                                        | Description                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `herdr`                     | [herdrdev/herdr](https://github.com/herdrdev/herdr)                                           | Drive the Herdr terminal multiplexer — panes, tabs and agents  |
| `openlogs-server-logs`      | [charlietlamb/openlogs](https://github.com/charlietlamb/openlogs)                             | Fetch and inspect local server logs via `openlogs tail`       |
| `pytorch-lightning`         | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Deep learning with PyTorch Lightning                          |
| `scikit-learn`              | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Machine learning with scikit-learn                            |
| `statistical-analysis`      | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Guided statistical analysis with test selection and reporting |
| `literature-review`         | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Systematic literature reviews across academic databases       |

## Third-Party Agents

| Agent              | Source                                                                                                           | Description                                          |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `data-scientist`   | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`data-ai/data-scientist`)          | Data science agent with access to all DS skills      |

## MCP Servers (Docker Toolkit)

MCP servers are provided via [MCP Toolkit by Docker](https://github.com/docker/mcp-toolkit). Install Docker Desktop and enable the MCP Toolkit extension, then configure servers through the Docker Desktop UI.

| Server            | Description                                                 |
| ----------------- | ----------------------------------------------------------- |
| AWS Documentation | Search AWS and AWSCC Terraform provider docs and IA modules |
| AWS Terraform     | Execute Terraform/Terragrunt commands and run Checkov scans |
| Context7          | Library documentation and code examples lookup              |
| GitHub Official   | Issues, PRs, commits, code search, repository management    |

## MCP Servers (CLI)

Some MCP servers are added directly via the `claude mcp add` CLI rather than the Docker Toolkit. Run these against this config directory so they land in the right `.claude` config:

```bash
export CLAUDE_CONFIG_DIR="$REPOS/claude-code-config/.claude"
```

| Server          | Transport | Endpoint / Command             | Description                |
| --------------- | --------- | ------------------------------ | -------------------------- |
| `linear-server` | http      | `https://mcp.linear.app/mcp`   | Linear issues and projects — added automatically by `install.sh` |

Sentry, Intercom, PostHog and Linear are installed by a separate work setup repo
instead — they are team tools, not personal config. Once that has run, drop the
`linear-server` row above with `claude mcp remove -s user linear-server`; it and
the Linear plugin point at the same URL.

`linear-server` is the one server `install.sh` registers for you. It writes it
into **every** config dir you might launch from, because which `.claude.json`
`claude mcp add` writes to is decided by `CLAUDE_CONFIG_DIR` at the time of the
call:

| Launcher | `CLAUDE_CONFIG_DIR` | Config file |
| -------- | ------------------- | ----------- |
| `cc` (see ZSH Configuration) | `<repo>/.claude` | `<repo>/.claude/.claude.json` |
| bare `claude` | unset | `~/.claude.json` |
| `CLAUDE_CONFIG_DIR=~/.claude claude` | `~/.claude` | `~/.claude/.claude.json` |

Registering in only one strands the server somewhere nothing reads — which is
exactly what happened before: it was added to `~/.claude/.claude.json` while
`cc` read the repo's copy and saw nothing.

Authentication is still interactive — run `/mcp` once after installing.

### Per-machine servers

The ClickHouse (`clickhouse-clippd-*`, `clickhouse-analytics-*`,
`clickhouse-scoreboard-*`) and Grafana (`grafana-mulligan-*`) servers are added
per machine, not managed here — they carry environment-specific credentials and
endpoints. They are deliberately absent from the `permissions.allow` list in
`settings.json`, so their tools prompt on first use.

### Permissions

`settings.json` allowlists MCP access at **server** level
(`mcp__plugin_context7_context7` covers every tool that server exposes) rather
than tool by tool, so a server gaining a tool doesn't need a config change.

Tools that write to systems outside this machine are then pulled back into `ask`,
which takes precedence over `allow`:

| Gated tool | Why |
| ---------- | --- |
| `mcp__MCP_DOCKER__mcp-add` / `__mcp-remove` / `__mcp-config-set` | Rewrites MCP server configuration |

Note that `MCP_DOCKER`'s `mcp-exec` and `code-mode` tools invoke other MCP
servers' tools, so they can reach a gated tool without triggering its `ask`
rule. Left allowed on the basis that gating them would gate the gateway
entirely; worth revisiting if that turns out to matter.

### Worktree env files

The `deny` list covers `Read`/`Edit` on `.env`, and Claude Code applies those
path rules to Bash commands as well — `cp .env <worktree>/` is denied, and a
deny is not approvable at the prompt. So `create-worktree` seeds a worktree
through a script instead: the repo's own `make worktree-env` /
`npm run worktree:env` where one exists, otherwise
`scripts/worktree-copy-env.sh`. Nothing in the command names a `.env` path, the
secrets stay out of the transcript, and the deny rules keep their scope.

### `rm` / `rmdir` / `mv` / `cp`

Glob rules cannot tell `rm -rf node_modules` from `rm -rf ~/Documents`, so these
four commands are gated by `.claude/scripts/guard-destructive.py` on `PreToolUse`
instead. It resolves every path the command would remove or overwrite —
expanding `~`, `$HOME` and `$PWD`, tracking a leading `cd`, and reducing a glob
to the directory it sits in — then answers:

| Verdict | When |
| ------- | ---- |
| `allow` | Inside the session's working tree, `$TMPDIR`, `/private/tmp`, `/private/var/folders`, or any other ordinary path |
| `ask`   | The working tree root itself, `.git`, or a path holding an unexpanded variable |
| `deny`  | `/`, the home directory, their top-level children, `~/Documents/RTM_REPOS`, and system trees |

Recursion is the difference between `rm *.pyc` and `rm -rf *`: a glob that
reduces to the working tree root is allowed without `-r`, and prompts with it.

A path outside the working tree is allowed — a sibling repo or worktree can be
deleted without a prompt, on the basis that the `deny` list already covers what
cannot be recreated. `~/Documents/RTM_REPOS` is in that list for the same reason:
its children are ordinary repos, but the directory holding all of them is not.

Three hook entries share the script, filtered by `if` so it only spawns for
commands mentioning `rm`, `mv` or `cp`. Emitting nothing leaves the
`allow`/`ask`/`deny` lists in charge, and a crash answers `ask`, so an
unparseable command prompts rather than running unchecked.

**Do not add blanket `Bash(rm *)`-style rules back to `ask`.** A rule outranks a
hook's `allow`, so those four entries made the `allow` verdict unreachable and
every in-tree `rm` prompted exactly as it did before the guard existed.

For the same reason the `deny` list keeps only the literal whole-machine wipes
(`rm -rf /`, `~`, `$HOME`) and `--no-preserve-root`. Path-shaped patterns such as
`Bash(*rm*/etc/*)` are gone: the guard already resolves those paths properly, and
the rule matched the *text* of the command, so a `grep` or an `echo` that merely
quoted the path was blocked with no way to override. With hooks off, `rm` and
friends fall back to a normal permission prompt.

## Audits

Comment and doc quality is the most common correction on generated work here,
and a rule in `CLAUDE.md` only helps if something checks it. Two audits do the
checking, and `/ship` is where they run:

| Detector                 | Finds                              | Hands off to        |
| ------------------------ | ---------------------------------- | ------------------- |
| `audit-comments-gate.py` | Comment lines the branch added     | `Agent(audit-comments)` |
| `audit-docs-gate.py`     | Docs the branch touched            | `Agent(audit-docs)` |

`Skill(ship)` runs both with `--list --scope branch` before it commits, and
spawns a subagent only for a detector that reported something. A branch that
touched no comments and no docs therefore costs two script runs and nothing
else.

**This used to be a `Stop` hook and is not any more.** Firing at the end of
every turn re-ran the same audit over the same branch a dozen times per PR,
which cost far more than it caught. Once per PR is the right frequency, and
`/ship` is the one command that marks a PR.

The audit runs **before** the commit, not after the PR, so the edits it makes
land inside the commit that opens the PR rather than trailing it in a
follow-up push.

Neither audit asks the main session to do the work. Each goes to a subagent —
`agents/audit-comments.md` and `agents/audit-docs.md`, both pinned to `haiku` —
which runs the matching skill, applies the edits and reports back. Reading every
touched file in full is the expensive half of an audit, and this keeps it out of
the main context.

The skills share the detectors via `--list`, so an audit covers exactly what was
reported. For comments that means a shallow scan for markers outside string
literals — `LINE_MARKERS` and `NAME_MARKERS` in the script are the list of file
types, and markdown is excluded since prose is not comments. For docs it means
the four well-known filenames plus anything under a `docs/` tree; generated and
mechanical markdown like `CHANGELOG.md`, `LICENSE.md` and `CODE_OF_CONDUCT.md`
are excluded on purpose, because a detector that reports files nobody maintains
claim by claim teaches you to ignore it.

They do not chain. `audit-comments` moves system-level facts out of comments and
into markdown, which makes that file a touched doc — but the two run
concurrently, so the docs audit picks it up on the next `/ship`.

The two detectors are separate scripts rather than one so either can be dropped
from `/ship` alone. They share `_audit_gate.py` for the git half, so their scope
semantics cannot drift apart.

Both are also available on demand as `/audit-comments` and `/audit-docs`:

- `/audit-comments` accepts a scope (`--staged`, `--working`), a PR number, paths, or `--dry-run`.
- `/audit-docs` accepts paths, a PR number, `--all`, or `--dry-run`.

The `statusLine` command in `settings.json` is written as
`"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/…"`. It runs through a shell, so
this resolves against whichever config dir is actually in use and needs nothing
from the installer.

## Required Plugins

| Plugin       | Marketplace                                                             | Install                                 | Description                          |
| ------------ | ----------------------------------------------------------------------- | --------------------------------------- | ------------------------------------ |
| `claude-mem` | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)       | `/plugin install claude-mem`             | Cross-session persistent memory      |
| `warp`       | [warpdotdev/claude-code-warp](https://github.com/warpdotdev/claude-code-warp) | `/plugin install warp@claude-code-warp` | Warp terminal integration            |
| `caveman`    | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)       | `/plugin install caveman@caveman`       | Compressed output mode — `/caveman`, plus `caveman-compress`, `caveman-stats` and `cavecrew` skills |
| `ponytail`   | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)   | `/plugin install ponytail@ponytail`     | "Lazy senior dev" mode — pushes for the smallest solution that works: YAGNI, stdlib first, one line over fifty |

These are declared in `.claude/settings.json` but their content must be fetched
after cloning — `./install.sh` does this, or do it by hand:

```bash
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

/plugin marketplace add warpdotdev/claude-code-warp
/plugin install warp@claude-code-warp

/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman

/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

`caveman` needs nothing per repo — its `SessionStart` hook keys off `~/.claude`,
so the mode applies everywhere. Its `/caveman-init` command writes rule files for
Cursor, Windsurf, Cline, Copilot and opencode and appends the same rule to
`AGENTS.md`; deliberately not run here, since nothing reads this repo but Claude
Code.

## Install

`./install.sh` installs this config into the global `~/.claude`, **replacing**
the managed items (`settings.json`, `agents/`, `skills/`, `scripts/`, `shared/`)
rather than merging into them. Anything it is about to overwrite is copied to
`~/.claude/backups/config-<timestamp>/` first. `CLAUDE.md`, credentials, plugins
and session state are left untouched.

Use the `make` targets:

```bash
make install       # replace the managed items
make install-full  # same, plus session state
```

| Target         | Runs                          | Effect                                                          |
| -------------- | ----------------------------- | --------------------------------------------------------------- |
| `install`      | `./install.sh`                | Replaces the managed items                                       |
| `install-full` | `./install.sh --session-state`| Also merges `projects/`, `sessions/`, `history.jsonl` (~1.5 GB)  |

Neither prompts. `./install.sh --dry-run` prints the plan and changes nothing.

**Run it from the main checkout, not a worktree.** The script resolves its
source `.claude` relative to its own location, so `make install` from inside
`.worktrees/<something>` installs *that worktree's* config.

Beyond copying files, it fetches the marketplaces and plugins declared in
`settings.json`, adds the `linear-server` MCP server if missing, and merges
`claude-mem/settings.json` into `~/.claude-mem`.

### `claude-mem` settings

`claude-mem/settings.json` at the repo root is the one managed thing that does
*not* live under `.claude/` — claude-mem reads `~/.claude-mem/settings.json`,
outside `CLAUDE_CONFIG_DIR` entirely, so the copy step never reaches it.

It is **merged** key-by-key, not replaced: the live file also holds provider API
keys and `CLAUDE_MEM_DATA_DIR`, which this repo deliberately does not track.
Tracked keys win; anything else in the target survives. `CLAUDE_CODE_PATH` is
resolved at install time from `command -v claude` rather than tracked, since it
is machine-specific.

Three of the tracked values exist to keep claude-mem's own `Stop` hook — which
this repo does not configure and cannot remove — from stalling every turn. That
hook is synchronous: it polls for its summary for up to 110s, against Claude
Code's own 120s hook timeout, so anything that stops a summary completing costs
you two minutes per turn, in every open session:

| Key | Value | Why |
| --- | ----- | --- |
| `CLAUDE_CODE_PATH` | resolved at install | Left empty, claude-mem resolves `claude` via `which` inside a worker daemon that outlives CLI updates. Once stale, every summary fails |
| `CLAUDE_MEM_EXCLUDED_PROJECTS` | `observer-sessions` | claude-mem summarises via Claude Code SDK subprocesses, which fire these same hooks and enqueue more summaries — self-feeding without this |
| `CLAUDE_MEM_MAX_CONCURRENT_AGENTS` | `6` | Sized to the number of sessions typically open at once. Beyond the cap, sessions fail with `Timed out waiting for agent pool slot` |

The worker caches settings at startup, so `install.sh` restarts it when one is
already running.

### `claude-mem` history

Nothing to migrate — memory is separate from the settings above. claude-mem
stores it in `~/.claude-mem`
(`claude-mem.db` + `chroma/`), resolved from `CLAUDE_MEM_DATA_DIR` →
`~/.claude-mem/settings.json` → that hardcoded default — never from
`CLAUDE_CONFIG_DIR`. Observations are keyed by project directory name, so recall
is identical whichever config dir Claude runs under.

What *is* per-config-dir is raw session state: `projects/` (transcripts),
`sessions/` (resumable sessions) and `history.jsonl` (prompt history). Those do
not follow a config-dir switch, which costs you `/resume` on old sessions and
↑-arrow prompt history but not memory recall. Pass `--session-state` to merge
them into the target — it is a merge, not a replace, so sessions already in the
target survive. The transcript corpus is large (~1.5 GB), so this is opt-in.

## ZSH Configuration

Add the following to `~/.zshrc` to launch Claude Code with different config directories:

```bash
cc() {
    CLAUDE_CONFIG_DIR=$REPOS/claude-code-config/.claude \
    claude --dangerously-skip-permissions "$@"
}
```
