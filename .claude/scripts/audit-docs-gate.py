#!/usr/bin/env python3
"""
Find the docs a change touches, for Skill(audit-docs).

Only the docs someone actually relies on count — the four well-known filenames
and anything under a docs/ tree. A CHANGELOG, a scratch note or a generated PR
body is markdown that nobody audits, and reporting those would train the reader
to ignore the list.

Unlike the comment detector this works at file granularity. There is no cheap
line-level signal for "this prose went stale", and the skill has to read the
whole file anyway to check a claim against the repo.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _audit_gate import (  # noqa: E402
    default_branch, git, skipped_path,
)

USAGE = (
    "usage: audit-docs-gate.py --list [--scope working|staged|branch] "
    "[--base REF] [PATH...]\n"
    "  Prints each touched doc as `path<TAB>+added/-removed`."
)

DOC_NAMES = {"CLAUDE.md", "AGENTS.md", "README.md", "REVIEW.md"}

# Generated or mechanical markdown: real docs by extension, but nothing a human
# maintains claim by claim.
SKIP_NAMES = {"CHANGELOG.md", "LICENSE.md", "CODE_OF_CONDUCT.md"}


def is_doc(path):
    if not path.endswith(".md") or skipped_path(path):
        return False
    base = os.path.basename(path)
    if base in SKIP_NAMES:
        return False
    if base in DOC_NAMES:
        return True
    # Whole segment, not substring — otherwise a skills/audit-docs/ directory
    # reads as a docs tree.
    return "docs" in path.split("/")[:-1]


def parse_numstat(raw, counts):
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if not is_doc(path):
            continue
        # Binary files report `-`; a doc should never, but don't crash if so.
        a = int(added) if added.isdigit() else 0
        r = int(removed) if removed.isdigit() else 0
        prev = counts.get(path, (0, 0))
        counts[path] = (prev[0] + a, prev[1] + r)


def collect(cwd, scope="working", base=None, paths=None):
    """Touched docs for the requested scope, as {path: (added, removed)}."""
    counts = {}
    paths = list(paths or [])
    pathspec = (["--"] + paths) if paths else []

    if scope == "staged":
        parse_numstat(git(["diff", "--cached", "--numstat"] + pathspec, cwd), counts)
        return counts

    if scope == "branch":
        ref = base or default_branch(cwd)
        merge_base = git(["merge-base", "HEAD", ref], cwd).strip() if ref else ""
        if merge_base and merge_base != git(["rev-parse", "HEAD"], cwd).strip():
            parse_numstat(git(["diff", "--numstat", merge_base] + pathspec, cwd), counts)
        else:
            parse_numstat(git(["diff", "--numstat", "HEAD"] + pathspec, cwd), counts)
    else:
        parse_numstat(git(["diff", "--numstat", "HEAD"] + pathspec, cwd), counts)

    # A doc that was just created is untracked, so no diff reaches it.
    for rel in git(["ls-files", "--others", "--exclude-standard"] + pathspec, cwd).splitlines():
        if not is_doc(rel):
            continue
        try:
            with open(os.path.join(cwd, rel), "r", encoding="utf-8", errors="replace") as fh:
                counts[rel] = (sum(1 for _ in fh), 0)
        except OSError:
            continue

    return counts


def run_list(argv):
    scope = "branch"
    base = None
    paths = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--scope" and i + 1 < len(argv):
            scope = argv[i + 1]
            i += 2
        elif arg == "--base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 2
        elif arg.startswith("--"):
            i += 1
        else:
            paths.append(arg)
            i += 1

    counts = collect(os.getcwd(), scope=scope, base=base, paths=paths)
    for path in sorted(counts):
        added, removed = counts[path]
        print(f"{path}\t+{added}/-{removed}")
    print(f"\n{len(counts)} touched doc(s), scope={scope}", file=sys.stderr)
    return 0


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--list":
        return run_list(argv[1:])
    # Exit 0, not 2. A session that started before this script stopped being a
    # Stop hook still calls it bare on every turn, and a non-zero exit there is
    # read as a block.
    print(USAGE, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
