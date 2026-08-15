"""
Shared plumbing for the audit-* detectors.

The two detectors differ only in what they look for. Keeping the git half here
is what stops their scope semantics from drifting apart.
"""

import subprocess

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
