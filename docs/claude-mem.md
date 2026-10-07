# claude-mem settings and history

## Settings

`claude-mem/settings.json` at the repo root, like `herdr/`, does *not* live under
`.claude/` — claude-mem reads `~/.claude-mem/settings.json`, outside
`CLAUDE_CONFIG_DIR` entirely, so the copy step never reaches it.

It is **merged** key-by-key, not replaced: the live file also holds provider API
keys and `CLAUDE_MEM_DATA_DIR`, which this repo deliberately does not track.
Tracked keys win; anything else in the target survives. `CLAUDE_CODE_PATH` is
resolved at install time from `command -v claude` rather than tracked, since it
is machine-specific.

Three of these settings exist to keep claude-mem's own `Stop` hook — which this
repo does not configure and cannot remove — from stalling every turn. That hook
is synchronous: it polls for its summary for up to 110s, against Claude Code's
own 120s hook timeout, so anything that stops a summary completing costs you two
minutes per turn, in every open session:

| Key | Value | Why |
| --- | ----- | --- |
| `CLAUDE_CODE_PATH` | resolved at install | Left empty, claude-mem resolves `claude` via `which` inside a worker daemon that outlives CLI updates. Once stale, every summary fails |
| `CLAUDE_MEM_EXCLUDED_PROJECTS` | `observer-sessions` | claude-mem summarises via Claude Code SDK subprocesses, which fire these same hooks and enqueue more summaries — self-feeding without this |
| `CLAUDE_MEM_MAX_CONCURRENT_AGENTS` | `6` | Sized to the number of sessions typically open at once. Beyond the cap, sessions fail with `Timed out waiting for agent pool slot` |

The worker caches settings at startup, so `install.sh` restarts it when one is
already running.

## History

Nothing to migrate — memory is separate from the settings above. claude-mem
stores it in `~/.claude-mem` (`claude-mem.db` + `chroma/`), resolved from
`CLAUDE_MEM_DATA_DIR` → `~/.claude-mem/settings.json` → that hardcoded default —
never from `CLAUDE_CONFIG_DIR`. Observations are keyed by project directory name,
so recall is identical whichever config dir Claude runs under.

What *is* per-config-dir is raw session state: `projects/` (transcripts),
`sessions/` (resumable sessions) and `history.jsonl` (prompt history). Those do
not follow a config-dir switch, which costs you `/resume` on old sessions and
↑-arrow prompt history but not memory recall. Pass `--session-state` to merge
them into the target — it is a merge, not a replace, so sessions already in the
target survive. The transcript corpus is large, so this is opt-in; `install.sh`
prints the size of each item as it merges it.
