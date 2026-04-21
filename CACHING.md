# Caching Architecture

This document describes how caching works across the Language Model Gateway
and its dependencies (`language-model-common`, `langchain-ai-skills-framework`).

---

## Overview

The gateway uses a multi-tier caching architecture to avoid redundant
disk/network I/O and to let new Gunicorn workers start quickly without
re-reading every config file from disk or GitHub.

| Layer | Scope | TTL env var | Default | Backed by |
|-------|-------|-------------|---------|-----------|
| **L1 -- In-memory config cache** | Per-worker process | `CONFIG_CACHE_TIMEOUT_SECONDS` | 3600 s | `ConfigExpiringCache` |
| **L2 -- Snapshot cache** | Cross-worker (shared) | `SNAPSHOT_CACHE_TTL_SECONDS` | 3600 s | MongoDB, file, or in-memory store |
| **L3 -- Disk / GitHub / S3** | Source of truth | -- | -- | Filesystem or remote |

Skills and plugins follow the same L1/L2/L3 pattern with their own
in-memory snapshots and the same shared L2 store.

MCP tool schemas have a separate in-memory cache with its own TTL.

---

## 1. Model Configuration Caching

### Data flow

```
Request
  |
  v
ConfigExpiringCache (L1, per-worker, short TTL)
  |  hit -> return
  |  miss
  v
Snapshot cache (L2, MongoDB/file, long TTL)
  |  hit -> populate L1, return
  |  miss
  v
Read from disk / GitHub / S3 (L3)
  |
  +-> write to L1 (ConfigExpiringCache.set)
  +-> write to L2 (_write_to_snapshot_cache)
  |
  v
Return models
```

### ConfigExpiringCache (L1)

An in-memory TTL cache holding `List[ChatModelConfig]`.

- **Class:** `ConfigExpiringCache` in `languagemodelcommon/utilities/cache/config_expiring_cache.py`
- **TTL:** `CONFIG_CACHE_TIMEOUT_SECONDS` (default `3600`)
- **Scope:** One instance per Gunicorn worker (singleton in DI container)
- **Thread safety:** `asyncio.Lock`
- **Stale fallback:** `get_stale()` returns the last value even after TTL
  expiry. Used when a disk read returns nothing (e.g. directory is mid-swap).

### Snapshot cache (L2)

Persists parsed `ChatModelConfig` objects so that new workers and restarts
can load configs from the cache instead of re-reading from disk or GitHub.

- **Factory:** `create_cache_store()` in `languagemodelcommon/utilities/cache/snapshot_cache_store.py`
- **Store types:**

  | `SNAPSHOT_CACHE_TYPE` | Class returned | Notes |
  |-----------------------|----------------|-------|
  | `mongo` | `ValidatingMongoDBStore` | Pings MongoDB on open (fail-fast) |
  | `file` | `FileStore` | JSON file at `/tmp/snapshot_cache/<collection>.json` |
  | `memory` | `MemoryStoreWithContextManager` | In-process only, lost on restart |

- **Singleton:** Registered as `BaseStore` in the DI container and shared
  by `ConfigReader`, `SkillkitDirectoryLoader`, and `MarketplaceDirectoryLoader`.
- **TTL:** `SNAPSHOT_CACHE_TTL_SECONDS` (default `3600`). This is
  independent of `CONFIG_CACHE_TIMEOUT_SECONDS`.
- **Collection:** `SNAPSHOT_CACHE_COLLECTION_NAME` (default `snapshot_cache`).
  Each data type can use its own collection via override env vars
  (see [Environment variables](#environment-variables)).
- **Fail-fast on `mongo`:** `ValidatingMongoDBStore` runs `db.command("ping")`
  during `__aenter__`. If MongoDB is unreachable the application fails to start
  instead of silently falling back.

### ConfigReader

- **File:** `languagemodelcommon/configs/config_reader/config_reader.py`
- **Cache key:** `model_configs`
- **Read behavior:** Errors from the snapshot store propagate (fail-fast).
- **Write behavior:** Errors propagate (fail-fast).
- **`clear_cache()`:** Clears both the in-memory `ConfigExpiringCache` and
  deletes the snapshot cache entry from the store.

### Double-check locking

`ConfigReader._read_base_models_async()` uses double-check locking to
prevent thundering-herd on cache miss:

1. Check L1 outside lock (fast path).
2. Acquire `asyncio.Lock`.
3. Check L1 again inside lock (another coroutine may have populated it).
4. Check L2 (snapshot cache).
5. Read from disk and write to both L1 and L2.

---

## 2. Skills and Plugins Caching

Skills (from `SkillkitDirectoryLoader`) and plugins (from
`MarketplaceDirectoryLoader`) follow the same three-tier pattern.

### Data flow (async path)

```
get_instructions() / list_skill_summaries()
  |
  v
In-memory _snapshot (L1, per-worker, TTL-based)
  |  valid -> return
  |  expired / empty
  v
MongoDB snapshot cache (L2, shared, TTL-based)
  |  hit -> populate L1, return
  |  miss
  v
Build snapshot from disk / GitHub (L3)
  |
  +-> write to L2 (best-effort)
  +-> set _snapshot + _snapshot_loaded_at (L1)
  |
  v
Return snapshot
```

### SnapshotCacheMixin

Both loaders inherit from `SnapshotCacheMixin`
(`langchain_ai_skills_framework/loaders/snapshot_cache_mixin.py`)
which provides:

| Method | Behavior |
|--------|----------|
| `_read_from_snapshot_cache()` | Best-effort read; returns `None` on any error |
| `_write_to_snapshot_cache()` | Best-effort write; failure logged at DEBUG |
| `_is_snapshot_valid_unlocked()` | Checks `_snapshot_loaded_at` against `_reload_ttl_seconds` |
| `_resolve_reload_ttl_seconds()` | Parses `SKILLS_CACHE_TIMEOUT_SECONDS`, defaults to 3600 |

### Cache keys

| Loader | Cache key | Collection env var |
|--------|-----------|--------------------|
| `SkillkitDirectoryLoader` | `skillkit_snapshot` | `SNAPSHOT_CACHE_SKILLS_COLLECTION` |
| `MarketplaceDirectoryLoader` | `marketplace_snapshot` | `SNAPSHOT_CACHE_PLUGINS_COLLECTION` |
| `ConfigReader` | `model_configs` | `SNAPSHOT_CACHE_MODEL_CONFIGS_COLLECTION` |

### refresh() vs refresh_async()

| Method | In-memory update | MongoDB write | Use case |
|--------|-----------------|---------------|----------|
| `refresh()` | Yes | No | Sync callers |
| `refresh_async()` | Yes | Yes | Background refresh loop |

The sync `_get_snapshot()` path never checks MongoDB -- it only checks
in-memory and falls back to disk. The async `_get_snapshot_async()` checks
in-memory, then MongoDB, then disk.

### Error handling difference

| Component | Read errors | Write errors |
|-----------|------------|--------------|
| `ConfigReader` | Propagate (fail-fast) | Propagate (fail-fast) |
| Skills/Plugins loaders | Return `None` (best-effort) | Swallow (best-effort) |

The rationale: model configs are critical for the gateway to function, so a
misconfigured snapshot cache should surface immediately. Skills and plugins
are additive features where a cache failure should not block the request.

---

## 3. MCP Tool List Caching

MCP tool schemas (the result of `list_tools` calls to MCP servers) are
cached to avoid redundant round-trips.

- **Class:** `ToolListCache` in `languagemodelcommon/mcp/mcp_client/tool_list_cache.py`
- **Scope:** In-memory dict, keyed by `url|auth_header`
- **TTL:** `MCP_TOOLS_METADATA_CACHE_TTL_SECONDS` (default `3600`).
  Falls back to `MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS` for backward
  compatibility.
- **Invalidation:** On HTTP 401 errors the entry for that server is
  invalidated so the next call re-fetches tools (potentially with a
  refreshed token).
- **`clear()`:** Wipes the entire cache. Not called during the periodic
  refresh loop -- tool schemas are assumed stable and expire naturally.

---

## 4. GitHub Config Repo Caching

When `GITHUB_CONFIG_REPO_URL` is set, the gateway downloads a zipball of
the configuration repo and extracts it to `GITHUB_CACHE_FOLDER`.

- **Class:** `GithubConfigRepoManager` in
  `languagemodelcommon/configs/config_reader/github_config_repo_manager.py`
- **Atomic swap:** Extraction goes to a staging directory; the live
  directory is swapped atomically so readers never see a partial tree.
- **Freshness check:** A timestamp marker file records when the last
  download happened. If the age is less than `CONFIG_CACHE_TIMEOUT_SECONDS`
  the download is skipped.
- **Background refresh:** A loop re-downloads and re-extracts every
  `CONFIG_CACHE_TIMEOUT_SECONDS`.

---

## 5. Startup and Refresh Lifecycle

### Startup (`lifespan` in `language_model_gateway/gateway/api.py`)

```
1. Open snapshot cache store          (MongoDB ping if type=mongo)
2. Download GitHub config repo        (if GITHUB_CONFIG_REPO_URL set)
3. Ensure skills directory exists
4. Initialize skills                  (MongoDB indexes + sync shared skills)
5. Eagerly load all configs           (_load_all_configs)
   a. read_model_configs_async()      -> populates L1 + L2
   b. skill_loader.get_instructions() -> populates L1 + L2 (async path)
6. Start background refresh task
```

### Background refresh (`_config_refresh_loop`)

Runs every `CONFIG_REFRESH_INTERVAL_MINUTES` (default `60`).

```
1. config_reader.clear_cache()
   -> clears L1 (ConfigExpiringCache)
   -> deletes L2 snapshot entry for model_configs
2. skill_loader.refresh_async()
   -> rebuilds skills + plugins from disk
   -> writes new snapshots to L2 (MongoDB)
3. _load_all_configs()
   -> read_model_configs_async()   -- rebuilds from disk, writes L1 + L2
   -> get_instructions()           -- returns fresh in-memory snapshot
```

### Manual refresh (`GET /refresh`)

Clears the in-memory and snapshot caches for model configs, then
re-reads from disk. Does not refresh skills or plugins.

---

## 6. Token / Authentication Caching

OAuth tokens are stored in MongoDB for reuse across requests. This is
separate from the config caching infrastructure.

- **Collection:** `MONGO_DB_TOKEN_COLLECTION_NAME` (default `tokens`)
- **Cache type:** `OAUTH_CACHE` (typically `mongo`)
- **Flow:** Authenticate -> store token -> reuse on subsequent requests
  -> refresh when expired

---

## 7. Environment Variables

### Model config caching

| Variable | Purpose | Default |
|----------|---------|---------|
| `CONFIG_CACHE_TIMEOUT_SECONDS` | L1 in-memory TTL + GitHub refresh interval | `3600` |
| `CONFIG_REFRESH_INTERVAL_MINUTES` | Background refresh loop interval | `60` |

### Snapshot cache (L2)

| Variable | Purpose | Default |
|----------|---------|---------|
| `SNAPSHOT_CACHE_TYPE` | Backend: `mongo`, `file`, `memory` | `memory` |
| `SNAPSHOT_CACHE_TTL_SECONDS` | Entry TTL in the persistent store | `3600` |
| `SNAPSHOT_CACHE_COLLECTION_NAME` | Default MongoDB collection | `snapshot_cache` |
| `SNAPSHOT_CACHE_MODEL_CONFIGS_COLLECTION` | Override collection for model configs | _(uses default)_ |
| `SNAPSHOT_CACHE_SKILLS_COLLECTION` | Override collection for skills | _(uses default)_ |
| `SNAPSHOT_CACHE_PLUGINS_COLLECTION` | Override collection for plugins | _(uses default)_ |

### Snapshot cache MongoDB connection

These fall back to the general `MONGO_URL` / `MONGO_DB_USERNAME` /
`MONGO_DB_PASSWORD` when the LLM-specific variants are not set.

| Variable | Purpose | Default |
|----------|---------|---------|
| `MONGO_LLM_STORAGE_URI` | MongoDB connection URL | `MONGO_URL` |
| `MONGO_LLM_STORAGE_DB_NAME` | Database name | `llm_storage` |
| `MONGO_LLM_STORAGE_DB_USERNAME` | Username | `MONGO_DB_USERNAME` |
| `MONGO_LLM_STORAGE_DB_PASSWORD` | Password | `MONGO_DB_PASSWORD` |

### MCP tool caching

| Variable | Purpose | Default |
|----------|---------|---------|
| `MCP_TOOLS_METADATA_CACHE_TTL_SECONDS` | Tool list cache TTL | `3600` |
| `MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS` | _(backward compat alias)_ | `3600` |

### Skills / plugins caching

| Variable | Purpose | Default |
|----------|---------|---------|
| `SKILLS_CACHE_TIMEOUT_SECONDS` | In-memory snapshot TTL | `3600` |

### GitHub config repo

| Variable | Purpose | Default |
|----------|---------|---------|
| `GITHUB_CONFIG_REPO_URL` | Zipball URL (disables download if unset) | _(none)_ |
| `GITHUB_CACHE_FOLDER` | Local extraction directory | `/tmp/github_config_cache` |
| `GITHUB_TOKEN` | PAT for authenticated access | _(none)_ |
| `GITHUB_TIMEOUT` | HTTP request timeout in seconds | `300` |

### Token / auth

| Variable | Purpose | Default |
|----------|---------|---------|
| `OAUTH_CACHE` | Cache backend (`mongo`, `memory`) | -- |
| `MONGO_DB_TOKEN_COLLECTION_NAME` | MongoDB collection for tokens | `tokens` |

---

## 8. Architecture Diagram

```
                         Gunicorn (N workers)
                  ┌──────────────────────────────────┐
                  │  Worker 1          Worker 2  ...  │
                  │  ┌──────────┐     ┌──────────┐   │
                  │  │L1 Config │     │L1 Config │   │
                  │  │  Cache   │     │  Cache   │   │
                  │  ├──────────┤     ├──────────┤   │
                  │  │L1 Skills │     │L1 Skills │   │
                  │  │ Snapshot │     │ Snapshot │   │
                  │  ├──────────┤     ├──────────┤   │
                  │  │L1 MCP    │     │L1 MCP    │   │
                  │  │ToolCache │     │ToolCache │   │
                  │  └────┬─────┘     └────┬─────┘   │
                  │       │                │          │
                  └───────┼────────────────┼──────────┘
                          │                │
                          v                v
                  ┌──────────────────────────────────┐
                  │       L2 Snapshot Cache           │
                  │  (MongoDB / File / Memory store)  │
                  │                                    │
                  │  Keys:                             │
                  │    model_configs                   │
                  │    skillkit_snapshot               │
                  │    marketplace_snapshot            │
                  └──────────────┬─────────────────────┘
                                 │
                                 v
                  ┌──────────────────────────────────┐
                  │         L3 Source of Truth        │
                  │                                    │
                  │  Filesystem  /  GitHub  /  S3      │
                  └──────────────────────────────────┘
```

Each worker has its own L1 caches. The L2 snapshot cache is shared
(via MongoDB) so that when Worker 2 starts, it can load model configs
and skills from L2 without hitting L3.