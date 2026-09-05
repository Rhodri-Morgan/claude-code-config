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
DO_PLUGINS=1
DO_SESSION_STATE=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

  --target DIR      Install into DIR instead of ~/.claude
  --dry-run         Print what would happen, change nothing
  --no-plugins      Files only; skip marketplaces, plugins and MCP servers
  --session-state   Also merge ${SESSION_STATE[*]} across (large)
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

# claude-mem reads ~/.claude-mem/settings.json, which sits outside CLAUDE_CONFIG_DIR
# and so is never touched by the copy above. Merged key-by-key rather than replaced:
# the live file also carries provider API keys and CLAUDE_MEM_DATA_DIR, none of which
# this repo tracks.
#
# CLAUDE_CODE_PATH is resolved here rather than tracked. Left empty, claude-mem
# resolves `claude` once via `which` inside a worker daemon that can outlive several
# CLI updates; when that goes stale every summary fails and the Stop hook — which
# polls for the summary synchronously — blocks each turn for its full 110s.
CM_SRC="$REPO_DIR/claude-mem/settings.json"
CM_FILE="$HOME/.claude-mem/settings.json"
if [[ -f "$CM_SRC" ]] && command -v jq >/dev/null; then
  info "merging claude-mem settings into $CM_FILE"
  if (( DRY_RUN )); then
    printf '    [dry-run] jq merge into %s\n' "$CM_FILE"
  else
    mkdir -p "$(dirname "$CM_FILE")"
    [[ -f "$CM_FILE" ]] || echo '{}' >"$CM_FILE"
    claude_bin="$(command -v claude || true)"
    [[ -n "$claude_bin" ]] || warn "claude not on PATH — leaving CLAUDE_CODE_PATH unset"
    tmp="$(mktemp)"
    jq -s --arg claude_bin "$claude_bin" \
      '.[0] * .[1] + (if $claude_bin == "" then {} else {CLAUDE_CODE_PATH: $claude_bin} end)' \
      "$CM_FILE" "$CM_SRC" >"$tmp"
    mv "$tmp" "$CM_FILE"

    # The worker caches settings at startup, so a running one keeps the old values.
    cm_port="$(jq -r '.CLAUDE_MEM_WORKER_PORT // "37777"' "$CM_FILE")"
    if curl -sf -m 5 "http://127.0.0.1:$cm_port/health" >/dev/null 2>&1; then
      cm_root="$(ls -dt "$HOME"/.claude/plugins/cache/thedotmack/claude-mem/[0-9]*/ 2>/dev/null | head -1)"
      if [[ -n "$cm_root" ]]; then
        info "restarting claude-mem worker to pick them up"
        node "${cm_root}scripts/bun-runner.js" \
          "${cm_root}scripts/worker-service.cjs" restart >/dev/null 2>&1 \
          || warn "claude-mem worker restart failed — restart it by hand"
      else
        warn "claude-mem worker is running but the plugin is not installed yet — restart it after the plugin step"
      fi
    fi
  fi
elif [[ -f "$CM_SRC" ]]; then
  warn "jq not found — skipping claude-mem settings merge"
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

cat <<EOF

$(info "done")
Interactive follow-ups this script cannot do for you:
  /mcp                            # authenticate the work MCP servers
  Docker Desktop → MCP Toolkit    # AWS docs/terraform, GitHub
EOF
