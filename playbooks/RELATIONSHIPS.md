# Relationships

Last verified: 2026-10-11 against b0d7252b by Claude

Who depends on this repo and what it depends on. This file is the source of truth; the bwell-repo-wiki page cites it. Evidence for consumers is the wiki page `repos/language-model-gateway.md` unless a repo path is given; this repo does not name its callers (unverified from this repo).

## Upstream: who calls or consumes this repo

| Consumer | What it uses | Contract it depends on | If you change... check | Evidence |
|---|---|---|---|---|
| baileyai | chat completions with a model config id | OpenAI-compatible response shape, streaming, auth | response shape, model ids | wiki page; unverified here |
| ai-visit-summary | chat completions via `gateway_base_url` | same | same | wiki page; unverified here |
| bai-evaluator | chat completions | same | same | wiki page; unverified here |
| data_science_rapid_prototyping | chat completions | same | same | wiki page; unverified here |
| OpenWebUI (local dev) | `/api/v1/models`, chat completions | OpenAI-compatible | `openwebui-config/functions/language_model_gateway_pipe.py` | repo path |

## Downstream: what this repo calls or depends on

| Dependency | What we use it for | How we reach it | Assumptions we make | Evidence |
|---|---|---|---|---|
| language-model-gateway-configuration (archived on GitHub; confirm where configs live now) | model and tool configs, loaded at startup and refreshed on an interval | mounted configuration directory (`language-model-gateway-configs/` locally) | read-only; reloads on the refresh interval or `GET /refresh` | `CACHING.md`, `docker-compose.yml` |
| language-model-common (`languagemodelcommon`) | shared provider, tool and MCP code | Python package, `>=2.0.99` | API of `SearchToolsTool`, `CallToolTool` | `pyproject.toml` |
| oidc-auth-lib (`oidcauthlib`) | token verification, token exchange | Python package | OIDC claims for tenancy | `.github/copilot-instructions.md` |
| mcp-server-gateway | MCP tool marketplace | `MCP_SERVER_GATEWAY_URL` | tool manifest shape | `docker-compose.yml`, `skill_publish_router.py` |
| mcp-fhir-agent | FHIR MCP tools declared by configs | URL in the config | tool names and auth | wiki page; unverified here |
| AWS Bedrock | model inference | `AWS_CREDENTIALS_PROFILE` | credentials | `README.md` |
| Azure OpenAI, OpenAI, Google (Gemini, search), Databricks, Tavily | optional providers and tools | keys in `.env.example` | optional | `.env.example` |
| MongoDB | token cache, DCR registrations, conversation memory, snapshot cache | `MONGO_URL`, `MONGO_LLM_STORAGE_URI` | tenant-isolated collections | `docker-compose.yml`, `api.py` |
| Okta, Keycloak (local) | OAuth | `AUTH_*` keys | | `.env.example`, `docker-compose-keycloak.yml` |

## If you change X, check Y

- Response shape or streaming of chat completions: every consumer row above.
- Model config ids: callers pin them; check `GET /api/v1/models` against caller configuration.
- `language-model-common` version: run the full test suite; the package owns tool and request wrapping.
- `MCP_SERVER_GATEWAY_URL` handling: the same variable name resolves to a different service in other stacks; check the target.

## Not a relationship

- `docker-compose-*.yml` services (Keycloak, OpenWebUI, Mongo, Postgres, inspector) are local development only.
- baileyai's tool binding and tool-availability logic live in baileyai, not here.

Next: [REVIEW.md](REVIEW.md) (blast radius for the PR).
