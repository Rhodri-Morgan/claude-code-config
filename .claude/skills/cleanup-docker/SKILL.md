---
name: cleanup-docker
description: Reclaim disk space from Docker — build cache, dangling and unused images, stopped containers, orphaned per-worktree compose stacks, and unused volumes. Use when the user wants to free up space, says "clean up docker", "prune docker", "docker is eating my disk", "reclaim space", or similar.
allowed-tools: Bash(docker:*), Bash(jq:*), Bash(test:*), Bash(ls:*), Bash(du:*), Bash(df:*), Bash(echo:*), Bash(printf:*), Bash(sort:*), Bash(awk:*), Bash(head:*), Bash(wc:*), Bash(command:*)
user-invocable: true
model: sonnet
---

# Cleanup Docker

Free disk space by removing Docker artefacts that are no longer backing live work: build cache, dangling and unused images, stopped containers, compose stacks whose worktree is gone, and unused volumes.

## Behavior

- **Report before removing.** Always print `docker system df` and the plan first, then act.
- **Local stacks are per-worktree and several run at once.** A stopped container is not necessarily dead work — it may be a stack the user will `make up` again tomorrow. Never assume a project is finished just because nothing is running.
- **Tiered, cheapest-and-safest first.** Only tier 1 runs unprompted. Everything below it costs either a rebuild or real data, so it needs confirmation.
- **Volumes are never pruned blind.** Local Postgres/Redis data lives in them. List them by name with their compose project, confirm, then remove.
- **Honour `$ARGUMENTS`:**
  - `--dry-run` — report the plan, remove nothing.
  - `--images` — include tier 3 (unused images).
  - `--volumes` — include tier 4 (unused volumes).
  - `--all` — tiers 1–3 plus orphaned stacks. Still not volumes; `--all --volumes` for that.
  - `--yes` — skip the confirmation prompts for whatever tiers were requested. Never assume it.

## Tiers

| Tier | What | Cost of getting it wrong | Runs by default |
| ---- | ---- | ------------------------ | --------------- |
| 1 | Dangling build cache, dangling images, non-compose stopped containers, unused networks | None — all of it is regenerable and unreferenced | Yes |
| 2 | Compose stacks whose config file no longer exists | Nothing, the worktree is gone | Ask |
| 3 | Images not referenced by any container, all build cache | A slow rebuild next time that stack starts | `--images` / `--all` |
| 4 | Unused volumes | Local database contents, permanently | `--volumes` |

## Workflow

### Step 1: Confirm Docker is up

```
!docker system df
```

If the daemon is not running, stop and say so — do not try to start Docker Desktop.

Keep this output. It is the "before" half of the final report.

### Step 2: Find orphaned compose stacks

Worktree stacks outlive their worktrees: `git worktree remove` deletes the directory but leaves the containers running, holding images, volumes and RAM against a compose file that no longer exists.

```
!docker compose ls -a --format json
```

For each project, split `ConfigFiles` on `,` and test each path. A project whose config files are **all** missing is orphaned.

```
!test -f "<config-path>"
```

A project whose config file still exists is live work — leave it alone regardless of whether it is running.

### Step 3: Size the tiers

```
!docker system df -v
```

Gives per-image, per-volume and per-container sizes. Use it to attribute reclaimable space to specific projects rather than reporting one bulk number.

For dangling volumes specifically:

```
!docker volume ls --filter dangling=true --format json
```

### Step 4: Print the plan

Group by tier, with sizes, and name what each thing belongs to:

```
Docker is using 66.3 GB, 24.0 GB reclaimable.

Tier 1 — safe, running now:
  build cache (dangling)            2.0 GB
  dangling images (7)               1.2 GB
  stopped non-compose containers (3)  40 MB
  unused networks (4)                  0 B

Tier 2 — orphaned stacks (worktree gone), needs confirmation:
  mulligan-rest-api-fix-ai-insights-perf         3 containers   1.1 GB
  mulligan-admin-feat-dev-tools-tab              1 container    260 MB
  ... 7 more

Tier 3 — unused images (--images):    6.5 GB   (forces a rebuild on next up)
Tier 4 — unused volumes (--volumes):  4.3 MB   (destroys local DB contents)

Keeping 7 live stacks: ai-insights-n-plus-one, cache-prefill, ...
```

If `$ARGUMENTS` contains `--dry-run`, stop here.

### Step 5: Tier 1 — safe prune

Runs without asking. **Order matters — images before build cache.**

```
!docker image prune -f
!docker container prune -f --filter "label!=com.docker.compose.project"
!docker network prune -f
!docker builder prune -f
```

Removing an image orphans the build-cache records that produced it, so a
`builder prune` before the image prune leaves most of the cache behind. Re-check
`docker system df` after the builder pass and run it again while Build Cache
RECLAIMABLE is non-zero — one pass on a stale machine took 2.0 GB, the second
pass immediately after the image prune took another 10.3 GB.

`label!=com.docker.compose.project` is what keeps this tier safe — it removes stray one-off containers and leaves every compose stack, running or stopped, intact.

### Step 6: Tier 2 — orphaned stacks

Only with confirmation (or `--yes`). `docker compose down` cannot help here: without a config file it has nothing to read. Work by project label instead.

Per orphaned project:

```
!docker ps -aq --filter "label=com.docker.compose.project=<project>" | xargs -r docker stop
!docker container prune -f --filter "label=com.docker.compose.project=<project>"
!docker network prune -f --filter "label=com.docker.compose.project=<project>"
```

**Pipe the IDs to `xargs`, never `docker stop $(...)` or `docker stop $ids`.** The
shell here is zsh, which does not word-split unquoted expansions — a multi-ID
variable arrives as one argument and the daemon answers `No such container: <id1>
<id2> <id3>`. `container prune` then finds nothing stopped and silently does
nothing, so the stack looks torn down in the command output while still running.
Always confirm with `docker compose ls -a` afterwards rather than trusting the
loop.

The project's volumes are tier 4 — they become dangling once the containers are gone, and are only removed if `--volumes` was passed.

### Step 7: Tier 3 — unused images

Only with `--images` or `--all`, and only with confirmation.

```
!docker image prune -af
!docker builder prune -af
```

`-a` on images removes anything no container references — including images for stacks that are merely stopped. `-a` on the builder drops the whole cache, not just the dangling part; it is usually the single biggest win and the only cost is a cold first rebuild.

### Step 8: Tier 4 — volumes

Only with `--volumes`, and always with an explicit confirmation naming what is about to go, even under `--yes`:

```
Removing 7 volumes (4.3 MB). This destroys their contents:
  mulligan-rest-api-fix-ai-insights-perf_pgdata   1.2 MB
  ...
```

```
!docker volume prune -f
```

To scope it to one dead project instead of everything dangling:

```
!docker volume prune -f --filter "label=com.docker.compose.project=<project>"
```

Tearing down a stack turns its volumes dangling, so the tier 4 total grows once
this step runs. Re-read it before reporting rather than quoting the figure from
step 4.

### Step 9: Report

Re-run `docker system df` and give the before/after in two or three lines:

```
Reclaimed 18.4 GB (66.3 GB → 47.9 GB).
Removed 9 orphaned stacks (27 containers), 12 images, all build cache.
Kept 7 live stacks and 25 volumes.
```

## Notes

- **The host disk may not shrink straight away.** Docker Desktop on macOS stores everything in a sparse VM disk image; space is returned to the daemon immediately but to APFS lazily. `docker system df` is the number that matters. If the host file genuinely needs to shrink, that is Docker Desktop → Settings → Resources → Disk usage, which is a manual, user-driven action — do not attempt it.
- **Never `docker system prune -a --volumes`.** It is the one command that does all four tiers at once, with no per-project visibility and no way to spare a stopped stack. The tiers exist precisely to avoid it.
- **`docker rm` and `docker volume rm` run unattended** — they match the `docker rm:*` and `docker volume rm:*` allow rules, and the destructive-command guard only reads plain `rm`/`rmdir`/`mv`/`cp`, not docker subcommands. The prune-with-filter forms above are still preferred where one call can express the same selection.
- **What a prune reports is not what `docker system df` shows.** `docker image prune` reports only the unique bytes it deleted; the df total drops by far more once shared layers stop being counted. Quote the df before/after as the headline number.
- Sizes from `docker system df -v` overlap — images share layers, so per-image sizes sum to more than the total. Report the totals from `docker system df` and treat the per-item numbers as attribution, not arithmetic.
- Stopping a container in an orphaned stack frees a port the worktree port scanner would otherwise skip, so this also unsticks port allocation drift over time.

## Examples

`/cleanup-docker`

1. Report: 66.3 GB used, 24.0 GB reclaimable, 9 orphaned stacks found
2. Run tier 1 → 3.2 GB back
3. Offer tiers 2–4 with sizes and stop

`/cleanup-docker --all`

1. Same report
2. Tier 1, then confirm and tear down the 9 orphaned stacks, then confirm and prune unused images and the full build cache
3. Leave volumes alone, say so

`/cleanup-docker --dry-run`

1. Report the plan across all four tiers
2. Remove nothing

`/cleanup-docker --volumes --yes`

1. Tier 1 unprompted
2. List the dangling volumes by name and still confirm before removing them
