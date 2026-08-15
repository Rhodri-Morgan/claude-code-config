#!/usr/bin/env python3
"""
Find the comment lines a change added, for Skill(audit-comments).

Detection is deliberately shallow: a marker at the start of a line, or one
outside any string on a line of code. Judging the comments is the skill's job;
this only decides whether there is anything to judge. False positives cost one
audit that concludes "nothing to fix" — false negatives cost a comment nobody
looks at again, so the checks lean permissive.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _audit_gate import (  # noqa: E402
    default_branch, git, skipped_path,
)

USAGE = (
    "usage: audit-comments-gate.py --list [--scope working|staged|branch] "
    "[--base REF] [PATH...]\n"
    "  Prints every added comment line as `path:line<TAB>text`."
)

MAX_ADDED_LINES_PER_FILE = 2000

LINE_MARKERS = {
    ".py": ("#",),
    ".pyi": ("#",),
    ".sh": ("#",),
    ".bash": ("#",),
    ".zsh": ("#",),
    ".yml": ("#",),
    ".yaml": ("#",),
    ".toml": ("#",),
    ".tf": ("#", "//"),
    ".tfvars": ("#", "//"),
    ".hcl": ("#", "//"),
    ".rb": ("#",),
    ".pl": ("#",),
    ".r": ("#",),
    ".js": ("//",),
    ".mjs": ("//",),
    ".cjs": ("//",),
    ".jsx": ("//",),
    ".ts": ("//",),
    ".tsx": ("//",),
    ".go": ("//",),
    ".java": ("//",),
    ".kt": ("//",),
    ".swift": ("//",),
    ".c": ("//",),
    ".h": ("//",),
    ".cc": ("//",),
    ".cpp": ("//",),
    ".hpp": ("//",),
    ".rs": ("//",),
    ".scala": ("//",),
    ".cs": ("//",),
    ".php": ("//", "#"),
    ".sql": ("--",),
    ".lua": ("--",),
    ".hs": ("--",),
    ".graphql": ("#",),
    ".gql": ("#",),
    ".prisma": ("//",),
    ".proto": ("//",),
    ".dart": ("//",),
    ".groovy": ("//",),
    ".gradle": ("//",),
    ".scss": ("//",),
    ".less": ("//",),
    ".ex": ("#",),
    ".exs": ("#",),
    ".nix": ("#",),
    ".jl": ("#",),
    ".ps1": ("#",),
    ".ini": ("#", ";"),
    ".cfg": ("#", ";"),
    ".conf": ("#",),
    ".properties": ("#",),
    # Block- or markup-only: no line marker, but still carry comments.
    ".css": (),
    ".html": (),
    ".htm": (),
    ".xml": (),
    ".vue": ("//",),
    ".svelte": ("//",),
}

NAME_MARKERS = {
    "Makefile": ("#",),
    "makefile": ("#",),
    "Dockerfile": ("#",),
    "Justfile": ("#",),
    "Procfile": ("#",),
    "Brewfile": ("#",),
    ".envrc": ("#",),
    ".gitignore": ("#",),
    ".dockerignore": ("#",),
    ".editorconfig": ("#",),
}

BLOCK_PREFIXES = ("/*", "*/", "* ", "*\t")
BLOCK_FAMILY = {
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".go", ".java", ".kt",
    ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".rs", ".scala", ".cs",
    ".php", ".tf", ".tfvars", ".hcl", ".css", ".scss", ".less", ".prisma",
    ".proto", ".dart", ".groovy", ".gradle", ".vue", ".svelte",
}

MARKUP_PREFIXES = ("<!--", "-->")
MARKUP_FAMILY = {".html", ".htm", ".xml", ".vue", ".svelte"}

SKIP_SUFFIXES = (".lock", ".min.js", ".min.css", ".map", ".snap")


def markers_for(path):
    """Comment markers for a path, or None if it has no comments worth auditing."""
    if skipped_path(path):
        return None
    if path.endswith(SKIP_SUFFIXES):
        return None

    base = os.path.basename(path)
    if base in NAME_MARKERS:
        return NAME_MARKERS[base]

    ext = os.path.splitext(path)[1].lower()
    return LINE_MARKERS.get(ext)


def trailing_comment_at(line, markers):
    """Index of a comment marker outside any string, or -1.

    Walks the line tracking quote state so a `#` in a query string or a `//` in
    a URL literal doesn't register.
    """
    quote = None
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            continue
        for marker in markers:
            if line.startswith(marker, i):
                # A marker glued to code (`a//b`, a `#` in a fragment) is more
                # often an operator or a URL than a comment.
                if i > 0 and not line[i - 1].isspace():
                    break
                return i
        i += 1
    return -1


def classify(line, path, lineno=0):
    """Return the comment text on an added line, or None."""
    markers = markers_for(path)
    # `()` is a real answer — CSS and HTML have comments but no line marker.
    if markers is None:
        return None

    stripped = line.strip()
    if not stripped:
        return None
    # Interpreter directives and bare closers are structure, not prose.
    if lineno == 1 and stripped.startswith("#!"):
        return None
    if stripped in ('"""', "'''", "*/", "-->"):
        return None

    for marker in markers:
        if stripped.startswith(marker):
            return stripped

    ext = os.path.splitext(path)[1].lower()
    if ext in BLOCK_FAMILY and stripped.startswith(BLOCK_PREFIXES):
        return stripped
    if ext in (".py", ".pyi") and (stripped.startswith('"""') or stripped.startswith("'''")):
        return stripped
    if ext in MARKUP_FAMILY and stripped.startswith(MARKUP_PREFIXES):
        return stripped

    idx = trailing_comment_at(line, markers)
    if idx > 0:
        return line[idx:].strip()
    return None


def parse_diff(diff, findings):
    """Collect added comment lines from a unified diff into `findings`."""
    path = None
    lineno = 0
    added_here = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
            added_here = 0
            continue
        if raw.startswith("@@"):
            try:
                new_part = raw.split("+", 1)[1].split(" ", 1)[0]
                lineno = int(new_part.split(",")[0])
            except (IndexError, ValueError):
                lineno = 0
            continue
        if not path or raw.startswith(("---", "diff ", "index ", "old mode", "new mode")):
            continue
        if raw.startswith("+"):
            added_here += 1
            if added_here <= MAX_ADDED_LINES_PER_FILE:
                text = classify(raw[1:], path, lineno)
                if text:
                    findings.append((path, lineno, text))
            lineno += 1
        elif raw.startswith(" "):
            lineno += 1


def collect(cwd, scope="working", base=None, paths=None):
    """Added comment lines for the requested scope, as (path, line, text)."""
    findings = []
    paths = list(paths or [])
    pathspec = (["--"] + paths) if paths else []

    if scope == "staged":
        parse_diff(git(["diff", "--cached", "--unified=0", "--no-color"] + pathspec, cwd), findings)
        return findings

    if scope == "branch":
        ref = base or default_branch(cwd)
        merge_base = git(["merge-base", "HEAD", ref], cwd).strip() if ref else ""
        # On the default branch itself there is no branch to diff, so this
        # degrades to the working tree rather than reporting the whole history.
        if merge_base and merge_base != git(["rev-parse", "HEAD"], cwd).strip():
            parse_diff(git(["diff", "--unified=0", "--no-color", merge_base] + pathspec, cwd), findings)
        else:
            parse_diff(git(["diff", "--unified=0", "--no-color", "HEAD"] + pathspec, cwd), findings)
    else:
        parse_diff(git(["diff", "--unified=0", "--no-color", "HEAD"] + pathspec, cwd), findings)

    # A file Claude has just written is untracked, and no diff reaches it —
    # which is the single most common way new comments arrive.
    untracked = git(["ls-files", "--others", "--exclude-standard"] + pathspec, cwd)
    for rel in untracked.splitlines():
        if not markers_for(rel):
            continue
        full = os.path.join(cwd, rel)
        try:
            if os.path.getsize(full) > 512_000:
                continue
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if n > MAX_ADDED_LINES_PER_FILE:
                        break
                    text = classify(line.rstrip("\n"), rel, n)
                    if text:
                        findings.append((rel, n, text))
        except OSError:
            continue

    return findings


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

    cwd = os.getcwd()
    findings = collect(cwd, scope=scope, base=base, paths=paths)
    for path, line, text in findings:
        print(f"{path}:{line}\t{text}")
    print(f"\n{len(findings)} added comment line(s), scope={scope}", file=sys.stderr)
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
