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
| GitHub Official   | Issues, PRs, commits, code search, repository management    |

## MCP Servers (CLI)

This repo registers no MCP servers of its own any more. Sentry, Intercom,
PostHog, and Linear come from the work setup repo, which installs each
server together with its read-only permission rules. Context7 is provided via the
official Claude Code plugins marketplace.

Do not register a `linear-server` MCP server pointing at
`https://mcp.linear.app/mcp`. The Linear plugin uses the same URL, and while a
hand-registered `linear-server` exists **the plugin's server never starts** —
it is shadowed rather than duplicated. If you have one:

```bash
claude mcp remove -s user linear-server
```

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
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/scripts/worktree-copy-env.sh`. Nothing in the command names a `.env` path, the
secrets stay out of the transcript, and the deny rules keep their scope.

### `rm` / `rmdir` / `mv` / `cp`

These four commands are gated by a `PreToolUse` hook,
`.claude/scripts/guard-destructive.py`, rather than glob rules, because glob
rules cannot tell `rm -rf node_modules` from `rm -rf ~/Documents`. The hook
allows paths in the working tree and ordinary paths, asks about the tree root
and `.git`, and denies whole-machine and home-level paths. The verdict table and
the reasoning are in [docs/destructive-commands.md](docs/destructive-commands.md).

## Audits

Two audits run from `/ship` before it commits: `audit-comments-gate.py` and
`audit-docs-gate.py` each list what the branch touched, and a Haiku subagent
audits only what a detector reported. The reasoning and the file lists are in
[docs/audits.md](docs/audits.md).

Both are also available on demand:

- `/audit-comments` accepts a scope (`--staged`, `--working`), a PR number, paths, or `--dry-run`.
- `/audit-docs` accepts paths, a PR number, `--all`, or `--dry-run`.

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
rather than merging into them. Those items are copied to
`~/.claude/backups/config-<timestamp>/` first. `CLAUDE.md`, credentials, plugins
and session state are not replaced; session state is merged only with
`--session-state`.

Use the `make` targets:

| Target              | Runs                           | Effect                                                                                                                                                        |
| ------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make install`      | `./install.sh`                 | Replaces the managed items                                                                                                                                    |
| `make install-full` | `./install.sh --session-state` | Also merges `projects/`, `sessions/`, `history.jsonl`                                                                                                         |
| `make install-vibe` | `./install.sh --vibe`          | Allows `gh pr merge`, `close` and `reopen`, and drops the main/master git denies (force-push, branch delete, `reset --hard`) in the installed `settings.json` |

None of them prompt. `./install.sh --dry-run` prints the plan and changes nothing.

Vibe mode lasts until the next plain `make install`. It edits the installed file
because a `deny` rule beats an `allow` from any other settings source, so a
`--settings` overlay could not lift it.

**Run it from the main checkout, not a worktree.** The script resolves its
source `.claude` relative to its own location, so `make install` from inside
`.worktrees/<something>` installs *that worktree's* config.

Beyond copying files, it fetches the marketplaces and plugins declared in
`settings.json`, merges `claude-mem/settings.json` into `~/.claude-mem`, and
copies `herdr/config.toml` to `~/.config/herdr/`.

### `herdr` config

`herdr/config.toml` is copied over `~/.config/herdr/config.toml` whole — it holds
no secrets or machine state. Skipped when identical; otherwise the old file is
kept beside it as `config.toml.bak-<timestamp>`. Edit the repo copy, not the live
one, or the next install reverts it.

### `claude-mem` settings

`claude-mem/settings.json` is merged key by key into `~/.claude-mem/settings.json`
rather than replacing it, and `install.sh` restarts a running claude-mem worker
so it picks the values up. Which keys are tracked, why, and how memory and
session state are stored is in [docs/claude-mem.md](docs/claude-mem.md).

## ZSH Configuration

Add the following to `~/.zshrc` to launch Claude Code with different config directories:

```bash
cc() {
    CLAUDE_CONFIG_DIR=$REPOS/claude-code-config/.claude \
    claude --dangerously-skip-permissions "$@"
}
```
