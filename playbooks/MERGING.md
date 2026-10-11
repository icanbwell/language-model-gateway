# Merging

Last verified: 2026-10-11 against b0d7252b by Claude

What has to happen to get an approved PR merged in this repo, beyond approval and green checks. Review criteria are in [REVIEW.md](REVIEW.md); what happens after the merge is in [DEPLOYMENT.md](DEPLOYMENT.md).

## Before you merge

1. `build_and_test` is green (`.github/workflows/build_and_test.yml`: runs `make run-pre-commit`, `make up`, then pytest in Docker). Expected by convention, not enforced: the `main` ruleset has no required status checks (`gh api repos/icanbwell/language-model-gateway/rules/branches/main`, 2026-10-11).
2. If `AGENTS.md` or `CLAUDE.md` changed, Enterprise Architecture review is expected by convention (`CODEOWNERS`: `@icanbwell/enterprise-architecture`), not enforced: the `main` ruleset has `require_code_owner_review: false`, so one approving review from anyone satisfies GitHub.
3. A dependency change updates `uv.lock` (`make update`).

## Merge mechanics

The `main` ruleset (2026-10-11) has only `non_fast_forward` and `pull_request` rules: 1 approving review from anyone, no required status checks. Merge method and auto-merge are unverified. Recent history on `main` shows squash-style subjects ending in `(#NNN)`. Target branch is `main`.

## What the merge triggers

`build_and_test` runs on push to `main`. Nothing deploys on merge: `deploy.yml` and `docker-publish.yml` are manual or release-triggered (see [DEPLOYMENT.md](DEPLOYMENT.md)).

## After you merge

Watch `build_and_test` on `main` to green. Release and deploy are separate human steps.

## Gotchas

- `docker-publish.yml` publishes images on a GitHub release being created; merging alone publishes nothing.

Next: [DEPLOYMENT.md](DEPLOYMENT.md).
