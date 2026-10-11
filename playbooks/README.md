# Playbooks

Last verified: 2026-10-11 against b0d7252b by Claude

Operational notes for `language-model-gateway`, written for someone already in the repo. Standard and templates: bwell-repo-wiki `docs/repo-playbooks/`. Edit by PR only.

Deployment status: this repo does not state whether the service is still running in any environment (unverified). The wiki page `repos/language-model-gateway.md` records the service as reported decommissioned and not confirmed against a live deployment. Confirm a live deployment before treating any monitoring or deploy step here as current.

| File | Come here if you are... |
|---|---|
| [MONITORING.md](MONITORING.md) | looking for logs, dashboards, monitors, databases or the deployment namespace |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | seeing a symptom and need the first checks |
| [MERGING.md](MERGING.md) | merging an approved PR, when this repo requires steps beyond approval and green checks |
| [LOGGING.md](LOGGING.md) | adding or changing log statements |
| [DEPLOYMENT.md](DEPLOYMENT.md) | releasing, deploying, or comparing test results before and after a deploy |
| [REVIEW.md](REVIEW.md) | reviewing a PR here, or preparing one for review |
| [RELATIONSHIPS.md](RELATIONSHIPS.md) | changing something other services depend on, or something this repo depends on |

When merging a PR, read MERGING.md, then DEPLOYMENT.md for what the merge triggers. When changing logging, read LOGGING.md; update MONITORING.md and TROUBLESHOOTING.md if the change affects what they point at.

Existing repo docs, linked from the file they relate to: [CACHING.md](../CACHING.md), [adrs/0001-structlog-for-json-log-rendering.md](../adrs/0001-structlog-for-json-log-rendering.md), [README.md](../README.md), [.github/copilot-instructions.md](../.github/copilot-instructions.md).
