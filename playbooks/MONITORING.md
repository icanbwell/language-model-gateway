# Monitoring

Last verified: 2026-10-11 against b0d7252b by Claude

Where to look when investigating this repo. This is where-to-look knowledge, not a findings ledger. Whether the service is currently deployed anywhere is unverified (see [README.md](README.md)).

## Groundcover

- Namespace per environment: the deploy workflow sets `SERVICE_NAMESPACE: language_model_gateway-${{ inputs.env }}` (`.github/workflows/deploy.yml`), env in dev, staging, perf, prod, client-sandbox. The Groundcover namespace and workload names are unverified (not stated in this repo); start with the Kubernetes namespace above and confirm with a workload listing.
- Query shape: filter by namespace and workload, then by the `level`, `logger`, `file`, `line` and `message` JSON fields (see [LOGGING.md](LOGGING.md)). Wide freetext searches in 3h chunks or smaller.
- No dashboard is referenced in this repo (unverified elsewhere).

## Dashboards and monitors

| Platform | What exists | Where |
|---|---|---|
| Groundcover dashboards | none referenced in this repo | unverified |
| Groundcover monitors | none referenced in this repo | unverified |
| Sigma | not applicable; not a data product | n/a |
| Mixpanel / PostHog | not applicable | n/a |
| Databricks | the gateway can query a Databricks SQL warehouse as a tool (`DATABRICKS_*` keys in `.env.example`); no dashboard | n/a |
| Sentry | none referenced in this repo | unverified |
| Prometheus metrics | `prometheus-fastapi-instrumentator` is a dependency (`pyproject.toml`); scrape target unverified | unverified |
| OpenTelemetry | local collector config `observability/otel-collector-config.yaml`, `docker-compose-otel.yml`; production export target unverified | repo paths |

## Log formats to know

- JSON, one object per line, fields `timestamp`, `level`, `logger`, `file`, `line`, `message`, optional `exception`, plus merged `extra_fields` (`language_model_gateway/gateway/utilities/logger/log_levels.py`). `LOG_FORMAT=text` switches to plain text.
- HTTP request tracing: `FastApiLoggingMiddleware` writes multi-line messages starting `==== Request ERROR:` and `====== Response ERROR :` for any response with status 300 or above, which includes the status and elapsed time (`language_model_gateway/gateway/middleware/fastapi_logging_middleware.py`). Each failure writes two lines. Success lines are DEBUG only.
- Startup lines `GLOBAL LOG_LEVEL:` and `<SOURCE>_LOG_LEVEL:` show the effective levels (`log_levels.py`).
- `/health` is excluded from the middleware and the uvicorn access log (`api.py`).

## Known noise

- `/health` accepts GET and POST and returns `OK` (`api.py`); it is filtered from logs, so its absence is expected.

## Databases

- MongoDB: database `language_model_gateway` locally (`MONGO_DB_NAME` in `docker-compose.yml`); collections `oauth_cache`, `tokens`, `dcr_registrations` (`MONGO_DB_AUTH_CACHE_COLLECTION_NAME`, `MONGO_DB_TOKEN_COLLECTION_NAME`, `MONGO_DB_DCR_COLLECTION_NAME`). Conversation memory and snapshot cache also use Mongo (`MONGO_LLM_STORAGE_URI`, `CACHING.md`). Deployed cluster, project and database names are unverified.
- Conversation lookup for Bailey turns: this repo does not own `bailey_messages`; see [baileyai's playbook](https://github.com/icanbwell/baileyai/tree/main/playbooks).

## Kubernetes / Deployment

- Namespace convention `language_model_gateway-<env>`; deploy target env `<env>-ue1`; helm chart version pinned in `deploy.yml`. No `.helm/` values files exist in this repo; where they live is unverified.
- Process model: gunicorn with workers set by `NUM_WORKERS` or core count, timeout `GUNICORN_TIMEOUT` (`Dockerfile`).

## Other

- Model and tool configuration is read from the configuration tree (`language-model-gateway-configs/` locally; deployed source is the separate `language-model-gateway-configuration` repo, loaded at startup, see `CACHING.md` for cache TTLs).
- Per-source log levels: `HTTP_TRACING`, `CONFIG`, `INITIALIZATION`, `HTTP`, `AUTH`, `TOKEN_EXCHANGE`, `DATABASE`, `LLM`, `FILES`, `IMAGE_GENERATION`, `IMAGE_PROCESSING`, `MCP`, `AGENTS`, `ERRORS`, `BAILEY`, each set with `<SOURCE>_LOG_LEVEL` (`log_levels.py`).
