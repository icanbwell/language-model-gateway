# Review

Last verified: 2026-10-11 against b0d7252b by Claude

Instructions for whoever reviews a PR in this repo, human or agent. Inherits the org review rubrics in `icanbwell/.github`; the org baseline wins on conflict. The repo's own review guidance is [.github/copilot-instructions.md](../.github/copilot-instructions.md); this file adds only what is specific.

## What makes this repo different

It fronts model providers and MCP tool servers behind one OpenAI-compatible API and handles caller tokens and on-behalf-of exchange. A change can silently alter which model, tools or credentials a caller gets. Callers and dependencies: [RELATIONSHIPS.md](RELATIONSHIPS.md).

## Rules

| # | Rule | Severity | How it is checked | Example |
|---|---|---|---|---|
| 1 | No tokens, Authorization headers or PHI in logs | BLOCKING | reviewer; see [LOGGING.md](LOGGING.md) | the middleware's header and body logging |
| 2 | Absolute imports, full type annotations, Ruff and mypy clean | BLOCKING | `make run-pre-commit` in `build_and_test` | `.pre-commit-config.yaml` |
| 3 | Tenant and token handling goes through `TokenExchangeManager`, `ToolAuthManager`, `oidcauthlib`; no ad-hoc env reads | BLOCKING | reviewer | `.github/copilot-instructions.md` |
| 4 | New dependencies are listed in `policies/approved-tech.yaml` or flagged | REVIEW | reviewer | structlog ADR |
| 5 | Changes to `AGENTS.md` / `CLAUDE.md` need Enterprise Architecture | CONVENTION (not enforced; `require_code_owner_review: false`) | CODEOWNERS | `CODEOWNERS`, ruleset on `main` |

## Evidence required by change type

| Change | Evidence the PR should carry |
|---|---|
| Behavior change | a failing test first, then passing `make tests` |
| Provider, model or tool wiring | tests under `tests/` for the provider; `RUN_TESTS_WITH_REAL_LLM` run if it affects real calls (unverified who runs it) |
| Dependency bump | pre-commit and CI green; `uv.lock` updated |
| Logging change | [LOGGING.md](LOGGING.md) checklist |

## Blast radius

Before approving, check [RELATIONSHIPS.md](RELATIONSHIPS.md): the response shape of `/api/v1/chat/completions` and `/api/v1/models`, auth requirements, streaming behavior, and the model config ids callers pin.

## Getting a PR reviewed

`CODEOWNERS` lists only `/AGENTS.md` and `/CLAUDE.md` (Enterprise Architecture); other paths have no automatic reviewer. Review channel and labels are unverified. Commit subjects in recent history are mixed: ticket-key prefix, conventional `chore(deps):`, or plain; a required review that has not been given blocks the merge even when someone else approved.

Next: once approved, [MERGING.md](MERGING.md).
