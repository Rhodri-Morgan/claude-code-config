#!/usr/bin/env bash
# Install this repo's Claude Code config into the global ~/.claude,
# replacing the managed items rather than merging into them.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/.claude"
TARGET="$HOME/.claude"

# Replaced wholesale. Everything else in the target (CLAUDE.md, credentials,
# plugins, history, session state) is left alone.
MANAGED=(settings.json agents skills scripts shared)

# Per-config-dir session state: transcripts, resumable sessions, prompt history.
# Merged in (never replaced) only with --session-state, since it is large and
# the target may have sessions of its own. claude-mem's own memory lives in
# ~/.claude-mem and is config-dir independent, so it needs no migration.
SESSION_STATE=(projects sessions history.jsonl)

DRY_RUN=0
ASSUME_YES=0
DO_PLUGINS=1
DO_SESSION_STATE=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

  --target DIR      Install into DIR instead of ~/.claude
  --dry-run         Print what would happen, change nothing
  --no-plugins      Files only; skip marketplaces, plugins and MCP servers
  --session-state   Also merge ${SESSION_STATE[*]} across (large)
  -y, --yes         Do not prompt before replacing
  -h, --help        This message

Replaces: ${MANAGED[*]}
Backs up anything it overwrites to <target>/backups/config-<timestamp>/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="${2:?--target needs a directory}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-plugins) DO_PLUGINS=0; shift ;;
    --session-state) DO_SESSION_STATE=1; shift ;;
    -y|--yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

run() {
  if (( DRY_RUN )); then
    printf '    [dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

[[ -d "$SRC" ]] || die "no .claude directory in $REPO_DIR"
command -v claude >/dev/null || warn "claude CLI not on PATH — plugin steps will be skipped"

# Installing onto the source would delete the repo's own files.
if [[ "$(cd "$SRC" && pwd -P)" == "$(cd "$TARGET" 2>/dev/null && pwd -P || echo /nonexistent)" ]]; then
  die "target is this repo's own .claude directory — nothing to do"
fi

info "source: $SRC"
info "target: $TARGET"

present=()
for item in "${MANAGED[@]}"; do
  [[ -e "$TARGET/$item" || -L "$TARGET/$item" ]] && present+=("$item")
done

if (( ${#present[@]} )); then
  info "will replace in $TARGET: ${present[*]}"
else
  info "nothing existing to replace"
fi

if (( ! DRY_RUN && ! ASSUME_YES )); then
  [[ -t 0 ]] || die "not a tty — re-run with --yes to confirm"
  read -r -p "Replace these with $SRC? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || die "aborted"
fi

run mkdir -p "$TARGET"

if (( ${#present[@]} )); then
  BACKUP="$TARGET/backups/config-$(date +%Y%m%d-%H%M%S)"
  info "backing up to $BACKUP"
  run mkdir -p "$BACKUP"
  for item in "${present[@]}"; do
    run cp -R "$TARGET/$item" "$BACKUP/$item"
  done
fi

for item in "${MANAGED[@]}"; do
  [[ -e "$SRC/$item" ]] || { warn "$item not in repo, skipping"; continue; }
  info "installing $item"
  run rm -rf "$TARGET/$item"
  run cp -R "$SRC/$item" "$TARGET/$item"
done

if (( DO_SESSION_STATE )); then
  for item in "${SESSION_STATE[@]}"; do
    [[ -e "$SRC/$item" ]] || { warn "$item not in source, skipping"; continue; }
    info "merging $item ($(du -sh "$SRC/$item" | cut -f1))"
    if [[ -d "$SRC/$item" ]]; then
      run mkdir -p "$TARGET/$item"
      # trailing /. merges contents, so sessions already in the target survive
      run cp -R "$SRC/$item/." "$TARGET/$item/"
    else
      run cp "$SRC/$item" "$TARGET/$item"
    fi
  done
fi

# The tracked statusLine command resolves via $RTM_REPOS, which is not set for
# every consumer of the global config — point it at the installed copy instead.
if [[ -f "$SRC/settings.json" ]] && command -v jq >/dev/null; then
  info "pointing statusLine at $TARGET/scripts/context-monitor.py"
  if (( DRY_RUN )); then
    printf '    [dry-run] jq statusLine.command rewrite\n'
  else
    tmp="$(mktemp)"
    jq --arg cmd "python3 $TARGET/scripts/context-monitor.py" \
      '.statusLine.command = $cmd' "$TARGET/settings.json" >"$tmp"
    mv "$tmp" "$TARGET/settings.json"
  fi
elif [[ -f "$SRC/settings.json" ]]; then
  warn "jq not found — statusLine still depends on \$RTM_REPOS"
fi

if (( ! DO_PLUGINS )); then
  info "done (--no-plugins)"
  exit 0
fi

if ! command -v claude >/dev/null || ! command -v jq >/dev/null; then
  warn "need both claude and jq for plugin/MCP steps — skipping"
  info "done"
  exit 0
fi

# Plugin and MCP state lives in the config dir, so the CLI must write to the
# target rather than wherever this shell happens to point.
export CLAUDE_CONFIG_DIR="$TARGET"

info "adding marketplaces"
while read -r repo; do
  [[ -n "$repo" ]] || continue
  printf '    %s\n' "$repo"
  run claude plugin marketplace add "$repo" || warn "marketplace add failed: $repo"
done < <(jq -r '.extraKnownMarketplaces // {} | to_entries[]
  | .value.source.repo // .value.source.url // empty' "$SRC/settings.json")

info "installing plugins"
while read -r plugin; do
  [[ -n "$plugin" ]] || continue
  printf '    %s\n' "$plugin"
  run claude plugin install "$plugin" --scope user || warn "plugin install failed: $plugin"
done < <(jq -r '.enabledPlugins // {} | to_entries[] | select(.value) | .key' "$SRC/settings.json")

info "checking MCP servers"
# `mcp add` defaults to local scope, which pins the server to whichever
# directory this ran from — a global install wants user scope.
#
# Which .claude.json it lands in is decided by CLAUDE_CONFIG_DIR at the time of
# the call, and there is more than one config dir in play: ~/.claude for a
# `CLAUDE_CONFIG_DIR=~/.claude claude`, this repo's .claude for the `cc`
# function in the README, and ~/.claude.json for a bare `claude`. Registering
# in only one strands the server somewhere nothing reads.
add_mcp_http() {
  local name="$1" url="$2" cfg="$3" label="$4"
  if jq -e --arg n "$name" '.mcpServers | has($n)' "$cfg/.claude.json" >/dev/null 2>&1; then
    printf '    %s already in %s\n' "$name" "$label"
  else
    printf '    %s → %s\n' "$name" "$label"
    run env CLAUDE_CONFIG_DIR="$cfg" claude mcp add --scope user \
      --transport http "$name" "$url" || warn "could not add $name to $label"
  fi
}

# $HOME is the config dir a bare `claude` uses (its config is ~/.claude.json).
MCP_CFGS=("$TARGET")
for extra in "$SRC" "$HOME"; do
  seen=0
  for existing in "${MCP_CFGS[@]}"; do
    if [[ "$extra" == "$existing" ]]; then seen=1; fi
  done
  if (( ! seen )); then MCP_CFGS+=("$extra"); fi
done

for cfg in "${MCP_CFGS[@]}"; do
  case "$cfg" in
    "$SRC")  label="repo checkout (\`cc\`)" ;;
    "$HOME") label="bare \`claude\`" ;;
    *)       label="$cfg" ;;
  esac
  add_mcp_http linear-server https://mcp.linear.app/mcp "$cfg" "$label"
done

cat <<EOF

$(info "done")
Interactive follow-ups this script cannot do for you:
  npx @posthog/wizard mcp add     # PostHog MCP server
  /mcp                            # authenticate Linear and Sentry
  Docker Desktop → MCP Toolkit    # AWS docs/terraform, Context7, GitHub
EOF
