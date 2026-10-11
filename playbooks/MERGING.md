# Merging

Last verified: 2026-10-11 against b0d7252b by Claude

What has to happen to get an approved PR merged in this repo, beyond approval and green checks. Review criteria are in [REVIEW.md](REVIEW.md); what happens after the merge is in [DEPLOYMENT.md](DEPLOYMENT.md).

## Before you merge

1. `build_and_test` is green (`.github/workflows/build_and_test.yml`: runs `make run-pre-commit`, `make up`, then pytest in Docker). Enforced by CI if it is a required check; branch-protection settings are unverified.
2. If `AGENTS.md` or `CLAUDE.md` changed, Enterprise Architecture review is required (`CODEOWNERS`: `@icanbwell/enterprise-architecture`). An approval from anyone else does not satisfy it.
3. A dependency change updates `uv.lock` (`make update`).

## Merge mechanics

Merge method, auto-merge, and required checks are unverified (not in the repo). Recent history on `main` shows squash-style subjects ending in `(#NNN)`. Target branch is `main`.

## What the merge triggers

`build_and_test` runs on push to `main`. Nothing deploys on merge: `deploy.yml` and `docker-publish.yml` are manual or release-triggered (see [DEPLOYMENT.md](DEPLOYMENT.md)).

## After you merge

Watch `build_and_test` on `main` to green. Release and deploy are separate human steps.

## Gotchas

- `docker-publish.yml` publishes images on a GitHub release being created; merging alone publishes nothing.

Next: [DEPLOYMENT.md](DEPLOYMENT.md).
