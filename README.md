# Claude Code Config

Personal Claude Code configuration.

## Third-Party Skills

| Skill                       | Source                                                                                        | Description                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
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

# PostHog (analytics) — installed via the PostHog wizard
npx @posthog/wizard mcp add
```

| Server          | Transport | Endpoint / Command             | Description                |
| --------------- | --------- | ------------------------------ | -------------------------- |
| `linear-server` | http      | `https://mcp.linear.app/mcp`   | Linear issues and projects — added automatically by `install.sh` |
| `posthog`       | wizard    | `npx @posthog/wizard mcp add`  | PostHog product analytics  |
| `sentry`        | plugin    | `sentry-mcp@sentry-mcp`        | Sentry issues, errors, and traces (provided by the `sentry-mcp` plugin) |

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
(`mcp__plugin_sentry-mcp_sentry` covers every tool that server exposes) rather
than tool by tool, so a server gaining a tool doesn't need a config change.

Tools that write to systems outside this machine are then pulled back into `ask`,
which takes precedence over `allow`:

| Gated tool | Why |
| ---------- | --- |
| `mcp__plugin_sentry-mcp_sentry__update_issue` | Mutates real Sentry issues |
| `mcp__MCP_DOCKER__mcp-add` / `__mcp-remove` / `__mcp-config-set` | Rewrites MCP server configuration |

Note that `MCP_DOCKER`'s `mcp-exec` and `code-mode` tools invoke other MCP
servers' tools, so they can reach a gated tool without triggering its `ask`
rule. Left allowed on the basis that gating them would gate the gateway
entirely; worth revisiting if that turns out to matter.

## Hooks

| Event  | Script                     | What it does |
| ------ | -------------------------- | ------------ |
| `Stop` | `audit-comments-gate.py`   | Blocks once if the turn added code comments, pointing at `Skill(audit-comments)` |

The comment gate exists because comment quality is the most common correction
on generated code here, and a rule in `CLAUDE.md` only helps if something checks
it. The script scans the **uncommitted** working tree, not the branch — scoping
it to the branch would re-litigate a long-lived branch's existing comments at
the start of every session. `/audit-comments` is the one that covers a whole PR.

It fires once per `session + HEAD`, so committing re-arms it for the next batch
of work; `AUDIT_COMMENTS_HOOK=0` turns it off for a session. State lives in
`~/.claude/state/audit-comments/` and is swept after seven days.

Detection is a shallow scan for comment markers outside string literals — it
decides whether there is anything to audit, not whether the comments are good.
The skill shares the same detector via `--list`, so an audit covers exactly what
the hook flagged. Roughly 60 extensions across the `#`, `//`, `--`, `/* */` and
`<!-- -->` families, plus `Makefile`-style filenames; the full table is in the
skill. Markdown, JSON and lockfiles are excluded.

Script paths in `settings.json` are written as
`$RTM_REPOS/claude-code-config/.claude/scripts/…`; `install.sh` rewrites that
prefix to the install target, since `$RTM_REPOS` is not set for every consumer
of the global config.

## Required Plugins

| Plugin       | Marketplace                                                             | Install                                 | Description                          |
| ------------ | ----------------------------------------------------------------------- | --------------------------------------- | ------------------------------------ |
| `claude-mem` | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)       | `/plugin install claude-mem`             | Cross-session persistent memory      |
| `warp`       | [warpdotdev/claude-code-warp](https://github.com/warpdotdev/claude-code-warp) | `/plugin install warp@claude-code-warp` | Warp terminal integration            |
| `sentry-mcp` | [getsentry/sentry-mcp](https://github.com/getsentry/sentry-mcp)         | `/plugin install sentry-mcp@sentry-mcp` | Sentry MCP server (errors, traces)   |

These are declared in `.claude/settings.json` but their content must be fetched
after cloning — `./install.sh` does this, or do it by hand:

```bash
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

/plugin marketplace add warpdotdev/claude-code-warp
/plugin install warp@claude-code-warp

/plugin marketplace add getsentry/sentry-mcp
/plugin install sentry-mcp@sentry-mcp
```

## Install

`./install.sh` installs this config into the global `~/.claude`, **replacing**
the managed items (`settings.json`, `agents/`, `skills/`, `scripts/`, `shared/`)
rather than merging into them. Anything it is about to overwrite is copied to
`~/.claude/backups/config-<timestamp>/` first. `CLAUDE.md`, credentials, plugins
and session state are left untouched.

Use the `make` targets:

```bash
make install       # prompts before replacing
make install-yes   # no prompt
make install-full  # same as install, plus session state
make install-full-yes
```

| Target         | Runs                          | Effect                                                          |
| -------------- | ----------------------------- | --------------------------------------------------------------- |
| `install`      | `./install.sh`                | Prompts before replacing                                         |
| `install-yes`  | `./install.sh --yes`          | No prompt — the prompt needs a tty, so this is the one an agent shell can use |
| `install-full` | `./install.sh --session-state`| Also merges `projects/`, `sessions/`, `history.jsonl` (~1.5 GB)  |
| `install-full-yes` | `./install.sh --session-state --yes` | The same, no prompt                                  |

**Run it from the main checkout, not a worktree.** The script resolves its
source `.claude` relative to its own location, so `make install` from inside
`.worktrees/<something>` installs *that worktree's* config.

Beyond copying files, it fetches the marketplaces and plugins declared in
`settings.json`, adds the `linear-server` MCP server if missing, rewrites
`statusLine.command` to the installed script path (so it no longer depends on
`$RTM_REPOS`), and merges `claude-mem/settings.json` into `~/.claude-mem`.

### `claude-mem` settings

`claude-mem/settings.json` at the repo root is the one managed thing that does
*not* live under `.claude/` — claude-mem reads `~/.claude-mem/settings.json`,
outside `CLAUDE_CONFIG_DIR` entirely, so the copy step never reaches it.

It is **merged** key-by-key, not replaced: the live file also holds provider API
keys and `CLAUDE_MEM_DATA_DIR`, which this repo deliberately does not track.
Tracked keys win; anything else in the target survives. `CLAUDE_CODE_PATH` is
resolved at install time from `command -v claude` rather than tracked, since it
is machine-specific.

Three of the tracked values exist to keep the `Stop` hook from stalling every
turn. That hook is synchronous — it polls for its summary for up to 110s, against
Claude Code's own 120s hook timeout — so anything that stops a summary completing
costs you two minutes per turn, in every open session:

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
