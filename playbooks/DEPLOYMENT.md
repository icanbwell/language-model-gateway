# Deployment

Last verified: 2026-10-11 against b0d7252b by Claude

How to release and deploy this repo. Whether any environment currently runs the service is unverified (see [README.md](README.md)).

## Pipeline

1. Merge to `main` ([MERGING.md](MERGING.md)).
2. Create a GitHub release. `.github/workflows/docker-publish.yml` (trigger: release created, or manual) builds the `production` Dockerfile target for amd64 and arm64 and pushes a multi-arch manifest to Docker Hub as `icanbwell/language_model_gateway:<tag>` and `latest`. Needs a human to create the release.
3. Run the `Deploy Workflow` (`.github/workflows/deploy.yml`, manual dispatch) with inputs `tag` and `env`. It uses `icanbwell/cie.gha-deploy` with the helm chart version pinned in the workflow, service namespace `language_model_gateway-<env>`, target `<env>-ue1`. Needs a human.
4. Whether the ECR or Docker Hub image is the one the cluster pulls is unverified.

## Environments

| Env | Purpose | Health URL | Notes |
|---|---|---|---|
| dev, staging, perf, prod, client-sandbox | options in `deploy.yml` | `/health` (GET or POST returns `OK`) | which are active, and which allow synthetic load, are unverified |

## Before and after a deploy

- **Test commands:** `make tests` (unit and functional in Docker); `make tests-integration` (runs `pytest tests` with `RUN_TESTS_WITH_REAL_LLM=1`, per the Makefile; it does not run `tests_integration/` and does not need `make up-integration`); `tests_integration/` holds one file, `test_aiden_api.py`, outside both targets; CI runs `pytest .` in the `language-model-gateway` compose service. Which need credentials: tests using a real LLM are gated by `RUN_TESTS_WITH_REAL_LLM` (`.env.example`), and `AWS_CREDENTIALS_PROFILE` is required for Bedrock. Reports are written to `reports/test-results.xml` in CI.
- **Before / after / compare / stop rule:** no baseline files or evaluation harness exist in this repo (unverified elsewhere). Compare the Groundcover `Response ERROR` counts for the same hours and weekday type ([MONITORING.md](MONITORING.md)).

## Release gotchas

- The image build needs the private package `language-model-common` from a private index configured in `pyproject.toml` (`[[tool.uv.index]]`); the credential name is unverified (not found in the Dockerfile on `origin/main`).
- Configuration is read at startup and refreshed by `_config_refresh_loop` every `CONFIG_REFRESH_INTERVAL_MINUTES` (default 60); `GET /refresh` clears the caches and re-reads from disk (`api.py`, `CACHING.md`). For a config-only change wait for the interval or call `/refresh`; restart only as a last resort.

## Verify in production

Check `GET /health`, then `GET /api/v1/models` lists the expected configs, then the `Response ERROR` rate from real traffic only. See [MONITORING.md](MONITORING.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Rollback

Redeploy the previous tag with the `Deploy Workflow` (read from the workflow; not exercised, unverified). It does not undo configuration changes made in `language-model-gateway-configuration` (archived on GitHub; confirm where configs live now).

Next: [MONITORING.md](MONITORING.md) to verify; if verification fails, [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
