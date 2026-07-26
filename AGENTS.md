# claude-code-config — Agent Instructions

This repository defines a Claude setup.

## Commands

| Intent                             | Target              |
| ---------------------------------- | ------------------- |
| See targets                        | `make`              |
| Install into `~/.claude`           | `make install`      |
| Install, including session state   | `make install-full` |

Use these targets to install — do not invoke `install.sh` directly.

`install.sh` resolves its source `.claude` relative to its own location, so
running it from a worktree installs *that worktree's* config into `~/.claude`.
Install from the main checkout.

## Internal Claude Config

Do not commit local runtime state, instead add to `.gitignore`.

### MCP permissions

Allowlist MCP access at **server** level in `settings.json`
(`mcp__plugin_sentry-mcp_sentry`, not each tool) so a server gaining a tool
needs no config change. Then pull individual tools that write to systems outside
this machine back into `ask` — `ask` takes precedence over `allow`.

Servers carrying environment-specific credentials (ClickHouse, Grafana) are
added per machine and stay out of the allowlist deliberately, so their tools
prompt on first use. Do not add them.

### Third-Party Components

When installing any third-party component (skill, agent, command, plugin, etc.) from an external source:

1. **Install verbatim** — do not trim, rewrite, or modify third-party files. Use them exactly as provided by the author.
2. **Document in README.md** — add the component name, source URL, and a short description to the appropriate table (Third-Party Skills, Third-Party Agents, Required Plugins, etc.).
