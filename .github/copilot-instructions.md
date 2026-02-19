# Language Model Gateway – Copilot Code Review Instructions

## Objectives
- Keep every change aligned with the OpenAI-compatible FastAPI gateway, LangChain/LangGraph providers, and MCP bridge that back OpenWebUI and downstream agents.
- Preserve strict typing (per `setup.cfg` mypy settings), absolute imports, Ruff/formatting/security hooks, and Pipenv lock integrity.
- Guard OAuth/OIDC, AWS credentials, and user content flowing through RequestScopeMiddleware, TokenStorageAuthManager, and MCP tool traffic; never leak tokens or PII.
- Maintain the Docker Compose + Makefile workflows that spin up Keycloak, Mongo, OpenWebUI, optional MCP stacks, and observability services.
- Deliver prioritized, actionable PR feedback that makes it easy for contributors to fix blocking issues first.

## Repository Context Summary
- Stack: Python 3.12, FastAPI, LangChain/LangGraph, GraphQL, Docker Compose, Keycloak (OIDC), MongoDB (token cache), PostgreSQL (OpenWebUI), AWS (S3/Bedrock via `AwsClientFactory`), httpx, OpenTelemetry, and Pipenv.
- Entry surface: `language_model_gateway/gateway/api.py` configures FastAPI, routers under `gateway/routers/`, middleware (`FastApiLoggingMiddleware`, `RequestScopeMiddleware`), static assets, and health endpoints.
- Business layers: managers in `gateway/managers/`, providers in `gateway/providers/`, converters/streaming helpers, MCP tooling (`gateway/mcp/**`), and tool implementations in `gateway/tools/`.
- DI/IoC: `LanguageModelGatewayContainerFactory.create_container()` registers services (Auth, TokenExchange, Tool/MCP providers, LangChain providers, persistence, caching) via `oidcauthlib.container.SimpleContainer`; `ContainerRegistry` + `Inject(...)` supply dependencies to routers, managers, and background jobs.
- AuthN/AuthZ: `oidcauthlib` (AuthRouter, AuthManager, TokenReader), PKCE helper `gateway/oidc_pkce_auth.py`, `TokenStorageAuthManager`, `TokenExchangeManager`, `ToolAuthManager`, and `TokenReducer` cooperate to handle on-behalf-of flows, OpenWebUI headers, and tool-scoped tokens.
- Config & env: use `language_model_gateway/configs/config_reader` + `ConfigExpiringCache` and `LanguageModelGatewayEnvironmentVariables` instead of ad-hoc `os.environ` access.
- Tests live in `tests/` (unit/functional) with dockerized execution; fixture data sits in repo (see `openwebui-config`, `language-model-gateway-configs`, etc.).
- Docker Compose files control the gateway, databases, Keycloak, MCP servers, observability (`docker-compose-otel.yml`), and OpenWebUI variants.

## Code Style and Quality Rules
- Absolute imports only (e.g., `from language_model_gateway.gateway.managers.chat_completion_manager import ChatCompletionManager`). No relative imports.
- Full type annotations for functions, class attributes, TypedDicts, and literals; prefer `Annotated[...]` for FastAPI dependencies. Avoid `Any` unless unavoidable and documented.
- `make run-pre-commit` must stay green (Ruff, formatting, mypy, security checks). When touching dependencies, update both `Pipfile` and `Pipfile.lock` via the documented make targets.
- Leverage existing abstractions:
  - Resolve services via `Inject(...)`/`Depends(...)` backed by `LanguageModelGatewayContainerFactory`; never instantiate managers/providers manually in routers or tools.
  - Reuse `LanguageModelGatewayEnvironmentVariables`, `ConfigReader`, `TokenReducer`, `LangGraphStreamingManager`, and `ModelFactory` rather than re-reading env vars or duplicating config parsing.
- MCP tooling: new remote tools must be registered through `MCPToolProvider`, include tracing/truncation interceptors, and respect `ToolAuthManager` token requirements. Local LangChain tools belong under `gateway/tools/` and should inherit existing base classes when possible.
- Logging: import `SRC_LOG_LEVELS`, call `logging.getLogger(__name__)`, and use `logger.exception("<message>")` inside `except` blocks to capture stack traces. Never log Authorization headers, JWTs, S3 paths with PHI, or OpenWebUI user details.
- Observability: when adding spans, obtain a tracer via `get_tracer("language_model_gateway.<module_path>")`, reuse existing span names where possible, and avoid placing secrets/PII in span attributes.

## Review Focus Areas
1. **Security & Privacy (blocking):** Keycloak/OIDC flows, PKCE helpers, RequestScopeMiddleware, TokenStorageAuthManager, TokenExchangeManager, and MCP tool auth must remain correct. No secrets in code. HTTPS for remote calls. Auth headers must never be logged or echoed back.
2. **Architectural Consistency (blocking):** Changes must fit the FastAPI router → manager → provider layering, DI patterns, and config/cache helpers. Chat completions must flow through `ChatCompletionManager`, LangChain/LangGraph providers, and `ToolProvider`/`MCPToolProvider`. New tools must wire through the DI container.
3. **Type Safety & Linting (blocking):** Full typing, no silent ignores, mypy per `setup.cfg`, Ruff, formatting, and security hooks must pass. Keep `Annotated` dependencies accurate.
4. **Tests & Reliability (blocking):** Add/extend tests under `tests/` for new routers, managers, providers, tools, or auth flows. Ensure they run via Docker (`make tests`). Favor dependency injection and fixtures over monkey patching.
5. **Performance & Resource Use (non-blocking unless severe):** Respect `TokenReducer` strategies, streaming constraints, MCP call timeouts, and `CONFIG_CACHE_TIMEOUT_SECONDS`. Avoid redundant external calls or large payloads (S3, Jira, Confluence, GitHub, Databricks).
6. **Documentation & DX (non-blocking but encouraged):** Update `README.md`, `add_new_agent.md`, or config docs when workflows/env vars change. Provide examples for new tools or endpoints.

## Blocking Issues (Must Fix Before Merge)
- Relative imports or direct instantiation that bypasses the DI container or `Inject(...)` dependencies.
- Missing/incorrect type annotations, `Any` leaks, or mypy/Ruff/pre-commit failures.
- Skipping `AuthManager`/`TokenReader`/`TokenExchangeManager` when handling user or tool tokens, or logging/returning tokens and PII.
- New routers/managers/providers not registered through `LanguageModelGatewayContainerFactory` or not resolved via `ContainerRegistry`.
- MCP tools that omit tracing/truncation interceptors, do not obtain tokens from `ToolAuthManager`, or ignore auth requirements defined in `AgentConfig`.
- Config or env access that bypasses `LanguageModelGatewayEnvironmentVariables`/`ConfigReader`, leading to inconsistent behavior across workers.
- Tests that cannot run with `make tests` or that rely on local resources outside the Compose stack.
- Dependency updates without synchronized `Pipfile`/`Pipfile.lock` changes.
- Run `make run-pre-commit` after a change to ensure the code passes linter.
- Don't put code in __init__.py files.

## Non-Blocking Suggestions (Nice to Have)
- Refactor duplicated logic in routers/managers/providers into shared helpers.
- Expand logging granularity using `SRC_LOG_LEVELS` categories (HTTP, MCP, LLM, etc.) when it aids debugging.
- Add lightweight smoke tests or fixtures for new external integrations (e.g., Confluence, Jira, GitHub, Databricks).
- Improve LangChain/LangGraph observability (span attributes, meaningful log context) without leaking sensitive data.
- Enhance docs with diagrams or flow descriptions for complex agent/tool additions.

## Security and Privacy Guidelines
- Always validate and refresh tokens through `TokenReader`/`AuthManager`; never trust headers blindly. Use RequestScopeMiddleware for per-request context.
- For PKCE/browser flows, use `OIDCAuthPKCE` and `AuthRouter`. For service-to-service flows, rely on `TokenExchangeManager` and `ToolAuthManager` with least-privilege scopes.
- When bridging to AWS (Bedrock, S3), honor `AWS_CREDENTIALS_PROFILE`, use `AwsClientFactory`, and never hardcode credentials.
- Sanitize data returned from Jira, Confluence, Databricks, GitHub, or MCP servers before logging or exposing to clients. Strip PHI/PII and redact secrets.
- Use HTTPS endpoints for remote services and verify certificates (see `make create-certs` for local TLS). Do not downgrade to HTTP except for the documented local dev hosts.
- Ensure cached tokens (`ConfigExpiringCache`, Mongo, persistence) honor TTLs and are invalidated on logout/refresh endpoints.

## Performance Guidelines
- Use `TokenReducer` strategies (`TOKEN_TRUNCATION_STRATEGY`) for large model inputs/outputs. Avoid manual truncation that conflicts with the configured strategy.
- Prefer streaming via `LangGraphStreamingManager` when responses may be large; fall back to buffered responses only when necessary.
- Reuse HTTP clients from `HttpClientFactory`/`LoggingTransport` and respect timeouts defined in `LanguageModelGatewayEnvironmentVariables`.
- Batched config reads should go through `ConfigReader` with caching, rather than re-reading YAML/GraphQL files per request.
- Be mindful of MCP tool fan-out; set appropriate tool lists/timeouts in `AgentConfig` to avoid thrashing remote servers.

## Testing Guidelines
- Run `make tests` (dockerized pytest) before submitting. Use `make tests-integration` when real LLM or external integrations are required (guard with env vars such as `RUN_TESTS_WITH_REAL_LLM`).
- Favor dependency injection and fixtures over monkey patching; leverage `oidcauthlib` container overrides or helper factories for mocks.
- Use `respx`/`httpx.MockTransport` for HTTP mocking, and provide deterministic data for GitHub/Jira/Confluence/Databricks helpers.
- Cover new FastAPI routes with request/response tests (can use `TestClient` inside dockerized pytest). Include negative cases for auth failures and token refresh paths.
- When adding MCP tools or interceptors, include async tests using the existing LangChain MCP adapters and stubbed servers where feasible.

## Dependencies and Build
- Pipenv is the source of truth. Update dependencies via `make Pipfile.lock`/`make update`, commit both `Pipfile` and `Pipfile.lock`, and rebuild containers if base images change.
- Use the provided Make targets: `make devsetup`, `make build`, `make up`, `make down`, `make up-open-webui`, `make up-open-webui-auth`, `make up-mcp-server-gateway`, etc. Never hand-edit Compose-managed resources without updating the relevant YAML.
- Pre-commit hooks live in `pre-commit-hook`; run `make setup-pre-commit` before committing and ensure `make run-pre-commit` passes locally and in CI.
- For images pulled from ECR (e.g., MCP server gateway), authenticate via `aws sso login` + `aws ecr get-login-password` as documented in `README.md`.

## Documentation and Examples
- Update `README.md`, `add_new_agent.md`, `openwebui-config/functions/readme.md`, or related docs whenever you add env vars, Make targets, OAuth steps, or tool workflows.
- Provide docstrings for routers, managers, tools, and MCP interceptors describing expected inputs/outputs and auth assumptions.
- When adding MCP agents or LangChain tools, include usage guidance (sample payloads, OpenWebUI instructions, or GraphQL queries) right in the docstrings plus any relevant docs folder.
- Keep `.env.example` synchronized with new environment variables and describe whether they are required or optional.

## Integration Points
- **OpenAI-compatible APIs:** `/api/v1/chat/completions`, `/api/v1/responses`, `/api/v1/images/*`, `/models`, `/refresh`, plus legacy `/graphql`. Ensure responses match OpenAI schemas in `gateway/schema/openai`.
- **Auth:** `/auth/*` routes from `AuthRouter`, PKCE login via `/auth/login`, refresh via `/refresh`, and OpenWebUI headers (`x-openwebui-user-*`).
- **OpenWebUI:** `make up-open-webui` (no auth) or `make up-open-webui-auth` (Keycloak/OIDC + SSL). Requires `/etc/hosts` entry for `keycloak` and certificates from `make create-certs`.
- **MCP:** Remote tools fetched through `MCPToolProvider` + LangChain MCP adapters; additional MCP stacks available via `docker-compose-mcp-*.yml` and `make up-mcp-*` targets.
- **External services:** AWS (Bedrock, S3), Jira/Confluence, GitHub, Databricks, ScrapingBee, Google Search. All integrations must go through the respective helper/factory to inherit auth, logging, and retry policies.

## Quick Start and Common Commands
- Initial setup: copy `.env.example` → `.env`, set `AWS_CREDENTIALS_PROFILE`, then run:
  ```sh
  make devsetup
  ```
- Bring the core stack up/down:
  ```sh
  make down
  make up
  ```
- Launch OpenWebUI variants:
  ```sh
  make up-open-webui       # no auth
  make up-open-webui-auth  # Keycloak + SSL + observability
  ```
- Run quality gates:
  ```sh
  make run-pre-commit
  make tests
  ```
- When working with MCP add-ons or observability: `make up-mcp-server-gateway`, `make up-mcp-fhir-agent`, `make up-mcp-inspector`, `make up-open-webui-ssl`, `make up-open-webui-auth` (also brings up Jaeger/otel).

## Enforcement Checklist for Reviewers
- Imports are absolute and modules resolve via the DI container; no manual singletons.
- Functions/classes are fully typed, and mypy/Ruff/pre-commit pass.
- Auth flows use `AuthManager`, `TokenReader`, `TokenExchangeManager`, and `ToolAuthManager` correctly; no secrets/PII in logs, spans, or responses.
- FastAPI routers call managers/providers rather than duplicating business logic; new services are registered in `LanguageModelGatewayContainerFactory`.
- MCP/LangChain tools honor tracing + truncation interceptors, token requirements, and config-driven URLs/timeouts.
- Tests cover new behavior and run with `make tests`; no reliance on undeclared local services.
- Docs/env samples updated for new endpoints, env vars, or workflows.
- Docker/Make targets remain usable; Compose files stay in sync with textual instructions.
