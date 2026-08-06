"""
Shared plumbing for the audit-* Stop hooks.

Both gates answer the same question — did this turn produce something worth
auditing, and have we already said so — and differ only in what they look for.
Keeping the git, state and block-emit halves here is what stops the two from
drifting into subtly different guard semantics.
"""

import json
import os
import subprocess
import sys
import time

# Claude Code has no `Stop` member in its hookSpecificOutput union, so the
# documented shape for blocking is guidance on stderr, decision JSON on stdout,
# exit 2. additionalContext is silently dropped on this path.
BLOCK_EXIT = 2

STATE_TTL_DAYS = 7

SKIP_DIRS = frozenset((
    ".worktrees", "node_modules", "vendor", "dist", "build", ".venv",
    ".next", "__pycache__", ".terraform", "site-packages", "coverage",
))


def git(args, cwd, check=False):
    try:
        out = subprocess.run(
            ["git"] + args, cwd=cwd, check=check,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def default_branch(cwd):
    ref = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd).strip()
    if ref.startswith("origin/"):
        return ref[len("origin/"):]
    for name in ("main", "master"):
        if git(["rev-parse", "--verify", "--quiet", name], cwd).strip():
            return name
    return ""


def skipped_path(path):
    """True if any directory in `path` is one we never audit.

    Matches whole segments — a substring test would swallow `rebuild/` along
    with `build/`.
    """
    return not SKIP_DIRS.isdisjoint(path.split("/")[:-1])


def state_path(name, session_id, head):
    root = os.path.join(os.path.expanduser("~"), ".claude", "state", name)
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, f"{session_id}-{head}")


def sweep_state(root):
    cutoff = time.time() - STATE_TTL_DAYS * 86400
    try:
        for entry in os.listdir(root):
            fp = os.path.join(root, entry)
            if os.path.getmtime(fp) < cutoff:
                os.remove(fp)
    except OSError:
        pass


def read_hook_input(env_switch):
    """Hook payload, or None if this fire should be a no-op.

    Covers the three ways a Stop hook should stay quiet: the kill switch, a
    payload it can't parse, and `stop_hook_active` — which is set while Claude
    is already continuing because of a Stop hook, and is what otherwise turns a
    blocking hook into an infinite loop.
    """
    if os.environ.get(env_switch) == "0":
        return None
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("stop_hook_active"):
        return None
    return payload


def already_fired(name, payload, cwd):
    """True if this gate has already blocked for this session at this commit.

    Keyed on HEAD as well as the session so that committing re-arms the gate for
    the next batch of work.
    """
    head = git(["rev-parse", "--short", "HEAD"], cwd).strip() or "nohead"
    session = payload.get("session_id") or "nosession"
    marker = state_path(name, session, head)
    sweep_state(os.path.dirname(marker))
    if os.path.exists(marker):
        return True
    try:
        with open(marker, "w") as fh:
            fh.write(str(int(time.time())))
    except OSError:
        pass
    return False


def block(reason):
    sys.stderr.write(reason)
    sys.stderr.flush()
    print(json.dumps({"decision": "block", "reason": reason}), flush=True)
    return BLOCK_EXIT
