---
name: cleanup-caches
description: Reclaim disk space from build and tool caches — Python bytecode, pytest/ruff/mypy, uv/pip/npm caches, optionally .venv, node_modules and .terraform provider downloads, and optionally the machine-wide caches (Xcode DerivedData, iOS simulators, Android AVDs, CocoaPods, Gradle, Playwright, Hugging Face). Use when the user wants to clear caches, says "clean caches", "clear python cache", "clear terraform cache", "my disk is full", or similar.
allowed-tools: Bash(find:*), Bash(du:*), Bash(df:*), Bash(ls:*), Bash(git worktree:*), Bash(git rev-parse:*), Bash(uv cache:*), Bash(pip cache:*), Bash(npm cache:*), Bash(yarn cache:*), Bash(bun pm cache:*), Bash(pod cache:*), Bash(brew cleanup:*), Bash(xcrun simctl:*), Bash(echo:*), Bash(printf:*), Bash(sort:*), Bash(awk:*), Bash(head:*), Bash(wc:*), Bash(command:*)
user-invocable: true
model: sonnet
---

# Cleanup Caches

Free disk space by removing caches that a tool will rebuild on its own: Python
bytecode and test/lint caches, the shared uv/pip/npm download caches, and — on
request — the per-project `.venv`, `node_modules` and `.terraform` directories.

## Behavior

- **Report before removing.** Size each group first, print the plan, then act.
- **Tiered.** Tier 1 costs nothing but CPU on the next run and goes unprompted.
  Tier 2 costs a network round trip (re-download, re-init) and needs
  confirmation.
- **Scope is the repo and its worktrees** by default, not the whole disk. Every
  worktree carries its own `.venv` / `node_modules` / `.terraform`, which is why
  the totals get large. `--machine` widens it to the home-directory caches.
- **Honour `$ARGUMENTS`:**
  - `--dry-run` — report the plan, remove nothing.
  - `--deep` — include tier 2.
  - `--global` — include the shared uv/pip/npm caches in tier 2.
  - `--machine` — include tier 3, the home-directory caches.
  - `--yes` — skip the tier 2 confirmation. Never assume it. It does **not**
    cover tier 3, which always confirms.
  - a path — clean that tree instead of the current repo.

## Tiers

| Tier | What | Cost of removing it | Runs by default |
| ---- | ---- | ------------------- | --------------- |
| 1 | `__pycache__`, `*.pyc`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.turbo`, `uv cache prune` | A slower first run | Yes |
| 2 | `.venv`, `node_modules`, `.terraform` | Re-download on next `uv sync` / `npm ci` / `terraform init` | `--deep` |
| 2 | `uv cache clean`, `pip cache purge`, `npm cache clean --force` | Re-download for *every* project on this machine | `--global` |
| 3 | Home-directory caches — see the table below | Varies: a rebuild, a re-download, or a re-install | `--machine` |

## Workflow

### Step 1: Establish the scope

```
!git rev-parse --show-toplevel
!git worktree list --porcelain
```

Clean the repo root and every worktree path it lists. Outside a git repo, or
when `$ARGUMENTS` names a path, use that directory.

### Step 2: Size each group

```
!find <root> -type d -name __pycache__ -prune -print0 | xargs -0 du -sch 2>/dev/null | tail -1
```

Repeat per group. `.venv`, `node_modules` and `.terraform` are usually two
orders of magnitude larger than the tier 1 groups — size them separately so the
plan shows where the space actually is.

### Step 3: Print the plan

```
Caches under claude-code-config (4 worktrees): 3.1 GB

Tier 1 — regenerable, running now:
  __pycache__ (212 dirs)        84 MB
  .pytest_cache (6)             12 MB
  .ruff_cache / .mypy_cache     31 MB
  uv cache prune (unreachable)  ~200 MB

Tier 2 — needs a re-download (--deep):
  .venv (4)                     1.2 GB
  node_modules (2)              980 MB
  .terraform (3)                610 MB   (terraform init before the next plan)

Tier 3 — machine-wide (--machine):
  CoreSimulator/Devices         19 GB
  .android/avd                  14 GB
  Xcode DerivedData            9.3 GB
  CocoaPods cache              6.3 GB
```

If `$ARGUMENTS` contains `--dry-run`, stop here.

### Step 4: Tier 1

Runs without asking:

```
!find <root> -type d -name __pycache__ -prune -exec rm -rf {} +
!find <root> -type f -name '*.pyc' -delete
!find <root> -type d \( -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name .turbo \) -prune -exec rm -rf {} +
!uv cache prune
```

`-prune` stops `find` descending into a directory it is about to delete, which
is what keeps `__pycache__` nested inside `.venv` from being walked twice.

`uv cache prune` removes only unreachable entries — wheels no environment on
this machine still points at. It is not the same as `uv cache clean`, which is
tier 2.

### Step 5: Tier 2 — per-project directories

Only with `--deep`, and only after confirmation naming the totals.

```
!find <root> -maxdepth 3 -type d \( -name .venv -o -name node_modules -o -name .terraform \) -prune -exec rm -rf {} +
```

`-maxdepth 3` keeps this to the project's own directories rather than the
copies vendored inside `node_modules`, which go with their parent anyway.

Never touch `.terraform.lock.hcl` — it is committed, and deleting it changes
which provider versions the next `init` resolves.

### Step 6: Tier 2 — shared caches

Only with `--global`, and only after confirmation. These are machine-wide: the
next `uv sync` in *any* repo re-downloads.

```
!uv cache clean
!pip cache purge
!npm cache clean --force
```

Skip any whose tool is not installed rather than reporting a failure.

### Step 7: Tier 3 — the machine-wide caches

Only with `--machine`, and only after confirmation naming the totals. `--yes`
does not cover this tier: these live outside any repo and several of them cost
a large re-download.

Size them first — a `du -sh` over the whole list, sorted, so the plan ranks by
what is actually there:

```
!du -sh <path> 2>/dev/null
```

Skip a path that does not exist rather than reporting it as zero.

**Tier 3a — rebuilt locally, no network.** Safe to offer as a group:

| Path | What | Cost of removing it |
| ---- | ---- | ------------------- |
| `~/Library/Developer/Xcode/DerivedData` | Xcode build products, indexes | A full rebuild + reindex per project |
| `~/Library/Developer/Xcode/Archives` | Shipped build archives | **Irreplaceable** — hold the dSYMs for released builds. Ask per archive, never bulk |
| `~/Library/Developer/Xcode/iOS DeviceSupport` | Symbols per physical device+iOS pair | Re-extracted next time that device is attached |
| `~/Library/Caches/com.apple.dt.Xcode` | Xcode's own scratch | Rebuild |
| `~/.gradle/caches/build-cache-*`, `~/.gradle/daemon` | Gradle build cache and daemon logs | A slower Android build |
| `~/Library/Caches/typescript`, `~/Library/Caches/node-gyp` | tsserver, native-module headers | Re-fetch, small |
| `~/Library/Caches/claude-cli-nodejs` | Claude Code's own cache | Rebuilt on next run |
| `~/.cache/pre-commit` | pre-commit hook environments | Re-created on next `pre-commit run` |

**Tier 3b — a re-download or a re-install.** Confirm these individually, naming
the size and what has to be re-fetched:

| Path | What | Cost of removing it |
| ---- | ---- | ------------------- |
| `~/Library/Developer/CoreSimulator/Devices` | iOS simulator devices — installed apps, their data, per-device disk | Apps reinstall; simulator state is lost. Prune per device, see below |
| Simulator runtimes | The iOS runtime disk images behind those devices | Multi-GB re-download from Apple. `xcrun simctl runtime list` |
| `~/.android/avd` | Android emulator AVDs — one qcow2 disk each | Re-create the AVD, re-download nothing if the system image stays |
| `~/Library/Android/sdk/ndk`, `.../system-images` | NDK versions and emulator system images | Re-download via `sdkmanager`, GB-scale |
| `~/Library/Caches/CocoaPods` | Pod specs and downloaded pods | `pod install` re-fetches |
| `~/.npm`, `~/.bun/install/cache`, `~/Library/Caches/Yarn`, `~/.pnpm-store` | JS package manager caches | Re-download on next install in *any* project |
| `~/.gradle/wrapper`, `~/.gradle/caches/modules-2` | Gradle distributions and resolved dependencies | Re-download on next build |
| `~/Library/Caches/ms-playwright`, `~/Library/Caches/Cypress` | Browser binaries | `npx playwright install` / `cypress install` |
| `~/.cache/huggingface`, `~/.ollama` | Model weights | The largest re-download of the lot. Never bulk-delete — list the models and ask |
| `~/Library/Caches/Homebrew`, `~/Library/Caches/JetBrains` | Downloaded bottles, IDE indexes | `brew cleanup` handles the first correctly; the second reindexes |
| `~/.m2/repository`, `~/.cargo/registry`, `~/go/pkg/mod`, `~/.sdkman` | JVM / Rust / Go / SDKMAN artifacts | Re-download per project |

Prefer the tool's own cleanup command over `rm -rf` wherever one exists — it
knows which entries are still referenced:

```
!brew cleanup --prune=all
!pod cache clean --all
!yarn cache clean
!bun pm cache rm
!xcrun simctl delete unavailable
```

**Stale per-branch simulators.** The worktree workflow leaves one simulator
device per branch — `xcrun simctl list devices` shows them named after the
branch (`feature/mul-651`, `fix/team-logo-fallback-fit`). Cross-reference
against `git branch -r` and offer to delete the ones whose branch is gone:

```
!xcrun simctl delete <udid>
```

`simctl delete unavailable` only removes devices whose *runtime* is gone — it
will not touch these, because their runtime is still installed.

### Step 8: Report

Two or three lines — reclaimed total, what went, what was left:

```
Reclaimed 3.1 GB.
Removed 212 __pycache__, 6 pytest caches, 4 .venv, 3 .terraform.
Kept node_modules (--deep only covers what was asked) and the shared uv cache.
```

Name any directory that now needs a re-init before it will build:
`terraform init` for each `.terraform` removed, `uv sync` for each `.venv`.

## Notes

- **Never delete `~/.terraform.d/plugin-cache`.** It is what makes re-`init`
  cheap after a `.terraform` removal — providers come from there instead of the
  registry. The destructive-command guard protects it anyway.
- **`.next`, `dist` and `build` are output, not cache.** They are cheap to
  rebuild but a running dev server will break mid-flight, so they are out of
  scope here.
- A `.venv` removed from a worktree takes its direnv state with it — the next
  `cd` re-renders `.env` from SSM, which needs AWS credentials to be live.
- **Docker is out of scope here** — `~/Library/Containers/com.docker.docker` is
  usually the single largest directory on the machine, but it is a VM disk
  image. Deleting files inside it reclaims nothing; `Skill(cleanup-docker)`
  prunes through the daemon instead.
- **`~/Library/Caches` also holds non-dev application caches** (Spotify, Chrome,
  Electron updater `*.ShipIt` directories). They can be large, but they are not
  build caches and are out of scope — mention them in the report if they
  dominate, and leave them.
- `find ... -exec rm -rf {} +` is not seen by the destructive-command guard,
  which only inspects the leading command word. The `-prune` and `-maxdepth`
  bounds above are therefore the only thing keeping the deletion scoped — do not
  relax them.

## Examples

`/cleanup-caches`

1. Size every group across the repo and its worktrees
2. Run tier 1 → ~300 MB back
3. Report tier 2 with sizes and stop

`/cleanup-caches --deep --yes`

1. Tier 1 unprompted
2. Remove `.venv`, `node_modules` and `.terraform` across all worktrees
3. Report which directories need `uv sync` / `terraform init`

`/cleanup-caches --dry-run`

1. Report the plan across all three tiers
2. Remove nothing

`/cleanup-caches --machine`

1. Tier 1 unprompted
2. Size the home-directory caches and rank them
3. Offer tier 3a as a group, tier 3b one at a time with the re-download named
4. List the branch-named simulator devices whose branch no longer exists
