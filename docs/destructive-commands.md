# Destructive command guard

`rm`, `rmdir`, `mv` and `cp` are gated by `.claude/scripts/guard-destructive.py`
on `PreToolUse`, not by glob rules. Glob rules cannot tell `rm -rf node_modules`
from `rm -rf ~/Documents`. The script resolves every path the command would
remove or overwrite — expanding `~`, `$HOME` and `$PWD`, tracking a leading
`cd`, and reducing a glob to the directory it sits in — then answers:

| Verdict | When |
| ------- | ---- |
| `allow` | Inside the session's working tree, `$TMPDIR`, `/private/tmp`, `/private/var/folders`, or any other ordinary path |
| `ask`   | The working tree root itself, `.git`, or a path holding an unexpanded variable |
| `deny`  | `/`, the home directory, their top-level children, `~/Documents/RTM_REPOS`, and system trees |

Recursion is the difference between `rm *.pyc` and `rm -rf *`: a glob that
reduces to the working tree root is allowed without `-r`, and prompts with it.

A path outside the working tree is allowed — a sibling repo or worktree can be
deleted without a prompt, on the basis that the guard's deny paths already cover
what cannot be recreated. `~/Documents/RTM_REPOS` is in that set for the same
reason: its children are ordinary repos, but the directory holding all of them
is not.

Three hook entries share the script, filtered by `if` so it only spawns for
commands mentioning `rm`, `mv` or `cp`. Emitting nothing leaves the
`allow`/`ask`/`deny` lists in charge, and a crash answers `ask`, so an
unparseable command prompts rather than running unchecked.

**Do not add blanket `Bash(rm *)`-style rules to `ask`.** A rule outranks a
hook's `allow`, so a blanket rule makes the `allow` verdict unreachable and every
in-tree `rm` prompts again.

For the same reason the `rm` deny entries in `settings.json` are limited to the
literal whole-machine wipes (`rm -rf /`, `~`, `$HOME`) and `--no-preserve-root`.
Path-shaped patterns such as `Bash(*rm*/etc/*)` are not used: the guard already
resolves those paths properly, and a pattern matches the *text* of the command,
so a `grep` or `echo` that merely quoted the path would be blocked with no way
to override. With hooks off, `rm` and friends are decided by the `allow`, `ask`
and `deny` lists alone.
