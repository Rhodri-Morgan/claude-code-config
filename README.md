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
| `ce-code-review`            | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Multi-persona code review of a PR or branch — security, maintainability, `CLAUDE.md`/`AGENTS.md` conformance |
| `ce-doc-review`             | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Review requirements, plans, and specs with role-specific lenses |
| `ce-resolve-pr-feedback`    | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Work through unresolved PR review threads and resolve them     |

### compound-engineering

The three `ce-*` skills are vendored from the [compound-engineering
plugin](https://github.com/EveryInc/compound-engineering-plugin) (v3.20.0,
MIT) — the review subset only, copied verbatim rather than installing the full
32-skill plugin. Update by re-copying `skills/<name>/` from upstream.

`/ce-code-review` is the main one. It reads the diff (current branch, a branch
name, or a PR URL — never checking out), picks reviewer personas from what the
diff actually touches, dispatches them as parallel subagents, then merges and
deduplicates their findings into one report with P0–P3 severities. Findings
that two personas independently agree on get promoted.

| Persona | Fires when the diff touches |
| ------- | --------------------------- |
| `correctness` | always |
| `project-standards` | always, when `CLAUDE.md` / `AGENTS.md` are discoverable — checks the diff against them |
| `security` | auth, public endpoints, user input, permission checks, secrets |
| `maintainability` | refactors, new abstractions, coupling/type-boundary changes, ≥200 changed lines |
| `testing`, `performance`, `api-contract`, `data-migration`, `reliability`, `adversarial`, `previous-comments` | their concern is present in the diff |

```bash
/ce-code-review                          # current branch, report only
/ce-code-review <PR number or URL>       # review a PR without checking it out
/ce-code-review base:origin/main         # current checkout against a ref
/ce-code-review apply:local              # authorise it to fix findings in place
```

Report-only by default — it will not touch the working tree without
`apply:local`, and it never pushes.

Notes on the vendored subset:

- Upstream prose references sibling skills that were **not** vendored
  (`ce-work`, `ce-plan`, `ce-brainstorm`, `ce-babysit-pr`). These are soft
  references — descriptions of upstream callers and artifact provenance, not
  runtime dependencies. The skills run standalone.
- Scripts are stdlib `python3` + `bash`; no extra dependencies.
- The optional cross-model adversarial pass shells out to a second provider CLI
  (`codex`, `cursor-agent`, `grok`). With none installed it falls back to the
  in-process `adversarial` persona.
- Plan discovery looks under `docs/plans/` by default; override with `docs_root`
  in a repo's `.compound-engineering/config.yaml`.

## Third-Party Agents

| Agent              | Source                                                                                                           | Description                                          |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `code-reviewer`    | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`development-tools/code-reviewer`) | Senior code reviewer for quality, security, and perf |
| `security-auditor` | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`security/security-auditor`)       | Security auditor for vulnerability analysis          |
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

# Supabase (read-only) — HTTP transport, auth via OAuth on first use
claude mcp add --transport http supabase \
  'https://mcp.supabase.com/mcp?read_only=true&features=database%2Cdebugging%2Cstorage%2Cdevelopment%2Cfunctions%2Cbranching'

# PostHog (analytics) — installed via the PostHog wizard
npx @posthog/wizard mcp add
```

| Server          | Transport | Endpoint / Command             | Description                |
| --------------- | --------- | ------------------------------ | -------------------------- |
| `linear-server` | http      | `https://mcp.linear.app/mcp`   | Linear issues and projects — added automatically by `install.sh` |
| `supabase`      | http      | `https://mcp.supabase.com/mcp` | Supabase database, storage and functions — pinned `read_only=true` |
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
make               # list targets
make install       # prompts before replacing
make install-full  # same, plus session state
```

| Target         | Runs                          | Effect                                                          |
| -------------- | ----------------------------- | --------------------------------------------------------------- |
| `install`      | `./install.sh`                | Prompts before replacing                                         |
| `install-full` | `./install.sh --session-state`| Also merges `projects/`, `sessions/`, `history.jsonl` (~1.5 GB)  |

For anything else — a dry run, a different target directory, skipping plugins,
or an unattended run — call the script directly:

```bash
./install.sh --dry-run       # show what would change, change nothing
./install.sh -y              # no prompt
./install.sh --no-plugins    # files only
./install.sh --target DIR    # somewhere other than ~/.claude
```

**Run it from the main checkout, not a worktree.** The script resolves its
source `.claude` relative to its own location, so `make install` from inside
`.worktrees/<something>` installs *that worktree's* config.

Beyond copying files, it fetches the marketplaces and plugins declared in
`settings.json`, adds the `linear-server` MCP server if missing, and rewrites
`statusLine.command` to the installed script path (so it no longer depends on
`$RTM_REPOS`).

### claude-mem history

Nothing to migrate. claude-mem stores its memory in `~/.claude-mem`
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
