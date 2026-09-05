#!/usr/bin/env python3
"""PreToolUse gate for rm / rmdir / mv / cp.

Resolves every path a destructive command would touch and returns one of:

  allow  inside the session's working tree or a temp dir
  ask    anywhere else, or when the path cannot be resolved statically
  deny   system roots, the home directory itself, and its top-level dirs

Returning nothing leaves the settings.json allow/ask/deny lists in charge, so a
crash or an unrecognised command shape degrades to prompting rather than to
silent execution.
"""

import json
import os
import shlex
import sys

DESTRUCTIVE = {"rm", "rmdir", "mv", "cp"}

# Wrappers to step over before deciding whether the command is destructive.
WRAPPERS = {"sudo", "command", "builtin", "nohup", "time", "env", "xargs", "exec", "\\rm"}

OPERATORS = {"&&", "||", ";", "|", "&", "(", ")", "\n", "<", ">", ">>"}

HOME = os.path.realpath(os.path.expanduser("~"))


def _home(*parts):
    return os.path.join(HOME, *parts)


# Deleting any of these, or anything above them, breaks the machine or loses
# data that has no other copy. Never allowed, never prompted.
PROTECTED = {
    "/",
    "/Applications",
    "/System",
    "/Library",
    "/Users",
    "/Volumes",
    "/bin",
    "/sbin",
    "/usr",
    "/etc",
    "/var",
    "/opt",
    "/dev",
    "/cores",
    "/private",
    "/private/etc",
    "/private/var",
    "/private/tmp",
    "/tmp",
    "/nix",
    HOME,
    _home("Applications"),
    _home("Desktop"),
    _home("Documents"),
    _home("Downloads"),
    _home("Library"),
    _home("Movies"),
    _home("Music"),
    _home("Pictures"),
    _home("Public"),
    _home(".ssh"),
    _home(".aws"),
    _home(".gnupg"),
    _home(".config"),
    _home(".local"),
    _home(".docker"),
    _home(".kube"),
    _home(".npm"),
    _home(".nvm"),
    _home(".terraform.d"),
    _home(".claude"),
    _home(".cursor"),
    _home(".vscode"),
    _home(".zshrc"),
    _home(".zprofile"),
    _home(".zshenv"),
    _home(".bashrc"),
    _home(".bash_profile"),
    _home(".profile"),
    _home(".gitconfig"),
    _home(".git-credentials"),
    _home(".netrc"),
}

# Anything below these is off-limits too, unless an allow root claims it first.
PROTECTED_TREES = (
    "/Applications",
    "/System",
    "/Library",
    "/bin",
    "/sbin",
    "/usr",
    "/etc",
    "/private/etc",
    "/var",
    "/private/var",
    "/opt",
    "/dev",
    "/Volumes",
    _home("Library"),
    _home(".ssh"),
    _home(".aws"),
    _home(".gnupg"),
    _home(".config"),
    _home(".docker"),
    _home(".kube"),
)

RANK = {"allow": 0, "ask": 1, "deny": 2}


def under(path, root):
    return path.startswith(root.rstrip("/") + "/")


def allow_roots(cwd):
    roots = [cwd, "/private/tmp", "/private/var/folders"]
    tmp = os.environ.get("TMPDIR")
    if tmp:
        roots.append(os.path.realpath(tmp))
    return [r for r in roots if r]


def segments(tokens):
    """Split a token stream into individual commands."""
    out, current = [], []
    for token in tokens:
        if token in OPERATORS:
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def command_of(tokens):
    """Return (name, args) if this segment runs a destructive command."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if "=" in token and not token.startswith("-") and token.split("=", 1)[0].isidentifier():
            i += 1
            continue
        name = os.path.basename(token.lstrip("\\"))
        if name in WRAPPERS:
            i += 1
            continue
        if name in DESTRUCTIVE:
            return name, tokens[i + 1 :]
        return None, []
    return None, []


def targets_of(name, args):
    """Paths the command writes to or removes, and whether it recurses."""
    paths, flags_done, conservative, recursive = [], False, False, False
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            conservative = True
            paths.append(arg)
            continue
        if not flags_done and arg == "--":
            flags_done = True
            continue
        if not flags_done and arg.startswith("-") and arg != "-":
            if arg == "--target-directory" or (not arg.startswith("--") and "t" in arg):
                skip_next = True
            elif arg.startswith("--target-directory="):
                paths.append(arg.split("=", 1)[1])
                conservative = True
            elif arg in ("--recursive", "-R") or (not arg.startswith("--") and "r" in arg.lower()):
                recursive = True
            continue
        paths.append(arg)

    if not paths:
        return None, recursive
    # cp only writes its destination; rm, rmdir and mv consume every argument.
    if name == "cp" and not conservative and len(paths) > 1:
        return paths[-1:], recursive
    return paths, recursive


def resolve(path, base):
    """Resolve one argument against `base`, the cwd in effect at that point."""
    if base is None:
        return None, False
    for var, value in (("HOME", HOME), ("PWD", base), ("TMPDIR", os.environ.get("TMPDIR", ""))):
        if value:
            path = path.replace("${%s}" % var, value).replace("$" + var, value)
    if any(ch in path for ch in "$`"):
        return None, False
    path = os.path.expanduser(path)
    # A glob stands for the contents of its parent, so judge the parent.
    globbed = False
    while any(ch in os.path.basename(path) for ch in "*?[") and os.path.dirname(path) != path:
        path, globbed = os.path.dirname(path) or ".", True
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.realpath(os.path.normpath(path)), globbed


def classify(path, cwd, globbed=False, recursive=False):
    if path is None:
        return "ask", "path is not statically resolvable"
    if path in PROTECTED or any(under(p, path) for p in PROTECTED):
        return "deny", f"{path} is a system or home-critical path"
    for root in allow_roots(cwd):
        if under(path, root):
            if os.path.basename(path) == ".git" or under(path, os.path.join(root, ".git")):
                return "ask", f"{path} is git metadata"
            return "allow", ""
        # A non-recursive glob only touches files sitting directly in the root,
        # not the tree below it.
        if path == root and globbed and not recursive:
            return "allow", ""
    if any(under(path, tree) for tree in PROTECTED_TREES):
        return "deny", f"{path} is inside a system directory"
    if path == cwd:
        return "ask", f"{path} is the working tree root"
    return "ask", f"{path} is outside the working tree"


def main():
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    cwd = os.path.realpath(payload.get("cwd") or os.getcwd())
    if not command:
        return None

    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None  # unparseable; the settings lists decide

    decision, reason, seen, base = "allow", "", False, cwd
    for segment in segments(tokens):
        name, args = command_of(segment)
        if not name:
            if segment and os.path.basename(segment[0]) == "cd":
                rest = [a for a in segment[1:] if not a.startswith("-")]
                base = resolve(rest[0], base)[0] if rest else HOME
            continue
        seen = True
        paths, recursive = targets_of(name, args)
        for path in paths or [None]:
            resolved, globbed = resolve(path, base) if path else (None, False)
            verdict, why = classify(resolved, cwd, globbed, recursive)
            if RANK[verdict] > RANK[decision]:
                decision, reason = verdict, why

    if not seen:
        return None
    return decision, reason


if __name__ == "__main__":
    try:
        result = main()
    except Exception as exc:  # noqa: BLE001 - never let a bug here open the gate
        result = ("ask", f"guard-destructive failed: {exc}")

    if result:
        verdict, reason = result
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": verdict,
                        "permissionDecisionReason": reason or "target is inside the working tree",
                    }
                }
            )
        )
