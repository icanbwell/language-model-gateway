---
name: migrate-pipenv-to-uv
description: Migrate a bwell Python repo from Pipenv + GitHub auth to uv + JFrog token auth. Converts Pipfile to pyproject.toml, updates Dockerfile, docker-compose, CI workflows, Makefile, pre-commit, and README.
when_to_use: When user asks to migrate from pipenv to uv, convert Pipfile to pyproject.toml, switch from GitHub auth to JFrog for private packages, or modernize Python dependency management.
argument-hint: "[target-repo-path]"
disable-model-invocation: true
user-invocable: true
allowed-tools: Read Write Edit Bash Grep Glob
effort: high
---

# Migrate Pipenv to uv + GitHub Auth to JFrog

You are migrating the repository at `$ARGUMENTS` (or the current working directory if no argument given) from Pipenv to uv, and from GitHub/.netrc-based private package auth to JFrog token-based auth.

Reference implementation: the `mcp-fhir-agent` repo's `convert-to-uv` branch.

## Before starting

1. Confirm the repo has a `Pipfile` and optionally `Pipfile.lock`
2. Check for existing `pyproject.toml` (may already have tool config)
3. Check for `setup.cfg` (tool config to migrate)
4. Identify which packages are private (hosted on JFrog, not PyPI)
5. Check for Dockerfile, docker-compose.yml, pre-commit files, Makefile, CI workflows

## Execution steps

Follow these steps in order. After each step, verify the change is correct before proceeding.

---

### Step 1: Create or extend `pyproject.toml`

**1a. Convert `[packages]` from Pipfile to `[project] dependencies`**

Read the Pipfile and map every entry under `[packages]` to PEP 621 format:
```
# Pipfile syntax                        -> pyproject.toml syntax
requests = ">=2.32.5"                   -> "requests>=2.32.5"
httpx = { version = ">=0.28.1", extras = ["http2"] } -> "httpx[http2]>=0.28.1"
pymongo = { version = ">=4.15.3", extras = ["snappy"] } -> "pymongo[snappy]>=4.15.3"
some_pkg = "*"                          -> "some_pkg"
some_pkg = "==1.2.3"                    -> "some_pkg==1.2.3"
```

Place these under `[project] dependencies = [...]`.

**1b. Convert `[dev-packages]` to `[dependency-groups] dev`**

```toml
[dependency-groups]
dev = [
    "pytest>=8.3.3",
    # ... all dev packages using same syntax mapping
]
```

**1c. Add JFrog index configuration**

Identify which packages are private (not on PyPI). Common ones: `fhir-to-llm`, `fhirnotesvectorstore`, `helix-fhir-client-sdk`, `devicecodex`, `oidcauthlib`. Check the Pipfile `[[source]]` sections for clues.

```toml
[[tool.uv.index]]
name = "jfrog"
url = "https://artifacts.bwell.com/artifactory/api/pypi/virtual-pypi/simple"
explicit = true

[tool.uv.sources]
# ONLY list packages that are private (not available on PyPI)
package-name = { index = "jfrog" }
```

`explicit = true` means only packages listed in `[tool.uv.sources]` query JFrog. Everything else uses PyPI.

**1d. Migrate tool config from `setup.cfg` to `pyproject.toml`**

If `setup.cfg` exists, migrate these sections:
- `[tool:pytest]` -> `[tool.pytest.ini_options]` (booleans: `True` -> `true`)
- `[mypy]` -> `[tool.mypy]`
- `[mypy-module.*]` sections -> `[[tool.mypy.overrides]]` with `module = ["module.name"]`
- `[pydantic-mypy]` -> `[tool.pydantic-mypy]`
- `[flake8]` -> delete (replaced by ruff if applicable)

---

### Step 2: Generate `uv.lock`

Tell the user to run:
```bash
export UV_INDEX_JFROG_USERNAME=""
export UV_INDEX_JFROG_PASSWORD="$JFROG_READ_TOKEN"
uv lock
```

Or if running inside Docker, this will be handled by the Dockerfile changes.

Commit `uv.lock` to the repo.

---

### Step 3: Update `.gitignore`

Find and replace the pipenv section:
```
# OLD
# pipenv
#Pipfile.lock

# NEW
# uv
.python-version
```

---

### Step 4: Update Dockerfile

Apply ALL of the following changes:

**4.1 Replace pipenv with uv binary:**
```dockerfile
# REMOVE
RUN pip install pipenv
ENV PIPENV_IGNORE_VIRTUALENVS=1

# ADD
COPY --from=ghcr.io/astral-sh/uv:0.11.6@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 /uv /uvx /usr/local/bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
```

**4.2 Replace .netrc auth with uv env vars:**
```dockerfile
# REMOVE: two secrets, .netrc file, trap cleanup
RUN --mount=type=secret,id=jfrog_user --mount=type=secret,id=jfrog_token \
    set -eu; \
    JFROG_USER=$(cat /run/secrets/jfrog_user); \
    JFROG_TOKEN=$(cat /run/secrets/jfrog_token); \
    trap 'rm -f ~/.netrc' EXIT; \
    echo "machine artifacts.bwell.com login $JFROG_USER password $JFROG_TOKEN" > ~/.netrc; \
    chmod 600 ~/.netrc; \
    pipenv sync --dev --system --verbose

# ADD: single secret, env vars (empty username = token auth)
RUN --mount=type=secret,id=jfrog_token \
    set -eu; \
    export UV_INDEX_JFROG_USERNAME=""; \
    export UV_INDEX_JFROG_PASSWORD="$(cat /run/secrets/jfrog_token)"; \
    uv sync --frozen --all-extras --no-install-project --verbose
```

**4.3 Replace Pipfile copy:**
```dockerfile
# REMOVE
COPY Pipfile* /usr/src/app/

# ADD
COPY pyproject.toml uv.lock* /usr/src/app/
```

**4.4 Replace system site-packages with venv copy:**
```dockerfile
# REMOVE
COPY --from=python_packages /usr/lib/python3.12/site-packages /usr/lib/python3.12/site-packages
COPY --from=python_packages /usr/local/bin /usr/local/bin
COPY --from=python_packages /usr/bin /usr/bin

# ADD
COPY --from=python_packages /opt/venv /opt/venv
```

**4.5 Add PATH in runtime stage:**
```dockerfile
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
```

**4.6 Create separate production/development stages:**

Structure the Dockerfile with these stages:
```dockerfile
# Stage 1: production dependencies
FROM base AS python_packages
RUN ... uv sync --frozen --all-extras --no-install-project --verbose
RUN cp -f uv.lock /tmp/uv.lock

# Stage 1b: dev dependencies (extends production)
FROM python_packages AS python_packages_dev
RUN ... uv sync --frozen --all-extras --group dev --no-install-project --verbose

# Stage 2: production runtime
FROM runtime-base AS production
COPY --from=python_packages /opt/venv /opt/venv
# ... app code only (NO tests), user setup, production CMD (gunicorn/uvicorn workers)

# Stage 3: development runtime (extends production with dev deps, tests, and hot reload)
FROM production AS development
USER root
COPY --from=python_packages_dev /opt/venv /opt/venv
COPY ./tests ${PROJECT_DIR}/tests
RUN chown -R appuser:appgroup /opt/venv ${PROJECT_DIR}/tests
USER appuser
# Override CMD with hot-reload for local development
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

# Default: bare `docker build .` produces production image
FROM production
```

Key points:
- The `production` stage has app code only — no `tests/` directory, no dev packages
- The `development` stage extends `production`, overlays the dev venv (superset), copies tests, and overrides CMD with hot reload
- The final `FROM production` ensures the default build target is production
- `docker-compose.yml` uses `target: development`, CI publish workflows use `target: production`

**4.7 Replace lock build arg:**
```dockerfile
# REMOVE
ARG RUN_PIPENV_LOCK=false

# ADD
ARG RUN_UV_LOCK=false
```

**4.8 Update lock file copy:**
```dockerfile
# REMOVE
COPY --from=python_packages ${PROJECT_DIR}/Pipfile.lock /tmp/Pipfile.lock

# ADD
COPY --from=python_packages /tmp/uv.lock /tmp/uv.lock
```

**4.9 Update chown:**
```dockerfile
# REMOVE
RUN chown -R appuser:appgroup ${PROJECT_DIR} /usr/lib/python3.12/site-packages /usr/local/bin /usr/bin

# ADD
RUN chown -R appuser:appgroup ${PROJECT_DIR} /opt/venv
```

**4.10 Remove `COPY ./setup.cfg`** if present.

---

### Step 5: Update `docker-compose.yml`

1. Add `target: development` to the build section
2. Remove `jfrog_user` from secrets (both in service and top-level `secrets:` block)
3. **CRITICAL**: Update ALL commented-out local package volume mounts from `/usr/local/lib/python3.12/site-packages/` or `/usr/lib/python3.12/site-packages/` to `/opt/venv/lib/python3.12/site-packages/`. If missed, developers who uncomment these will silently get the installed version instead of their local checkout.

---

### Step 6: Update `pre-commit.Dockerfile`

Replace pipenv with uv, remove `jfrog_user` secret, use uv env var auth. Keep `--group dev` since pre-commit linters need both prod and dev imports to type-check test files.

---

### Step 7: Update `pre-commit-hook` shell script

Remove `JFROG_READ_USER` validation and `--secret id=jfrog_user` from docker build command.

---

### Step 8: Update Makefile

Search and replace across the entire file:
- `Pipfile.lock` target -> `uv.lock`
- `RUN_PIPENV_LOCK` -> `RUN_UV_LOCK`
- Remove all `JFROG_READ_USER` checks
- Remove all `--secret id=jfrog_user,env=JFROG_READ_USER`
- `docker cp $$CONTAINER_ID:/tmp/Pipfile.lock Pipfile.lock` -> `docker cp $$CONTAINER_ID:/tmp/uv.lock uv.lock`
- Update `update:` target dependency from `Pipfile.lock` to `uv.lock`
- Add jfrog_token secret to `build-python-packages` target if missing

---

### Step 9: Update GitHub Actions workflows

Search ALL `.github/workflows/*.yml` files for:
- `JFROG_READ_USER` -> remove every occurrence
- `jfrog_user` -> remove every occurrence
- Build/test workflows: add `target: development`
- Docker publish workflows: add `target: production`

---

### Step 10: Update README

Replace GitHub CLI auth instructions (brew install gh, gh auth login, unset GITHUB_TOKEN) with:
```
Private packages (list-them) are hosted on JFrog. Set `JFROG_READ_TOKEN` in your environment before building:
export JFROG_READ_TOKEN="<your-jfrog-token>"
Add it to ~/.zshrc or ~/.bashrc to persist across sessions.
```

Update references from `setup.cfg` to `pyproject.toml`.

---

### Step 11: Delete old files

- `Pipfile`
- `Pipfile.lock`
- `setup.cfg` (if all config migrated)

---

### Step 12: Verify VERSION file

If `pyproject.toml` uses dynamic versioning, ensure `VERSION` file exists:
```toml
dynamic = ["version"]
[tool.setuptools.dynamic]
version = { file = "VERSION" }
```

---

## Verification checklist

After completing all steps, verify:

- [ ] `pyproject.toml` has all deps from Pipfile `[packages]` in `[project] dependencies`
- [ ] `pyproject.toml` has all deps from Pipfile `[dev-packages]` in `[dependency-groups] dev`
- [ ] `pyproject.toml` has `[[tool.uv.index]]` for JFrog with `explicit = true`
- [ ] `pyproject.toml` has `[tool.uv.sources]` listing only private packages
- [ ] `pyproject.toml` has tool config migrated from `setup.cfg`
- [ ] `uv.lock` generated and committed
- [ ] `Pipfile`, `Pipfile.lock`, `setup.cfg` deleted
- [ ] Dockerfile uses uv binary copy, not `pip install pipenv`
- [ ] Dockerfile uses `UV_PROJECT_ENVIRONMENT=/opt/venv` with PATH
- [ ] Dockerfile auth uses env vars (no .netrc)
- [ ] Dockerfile has production/development stages with `FROM production` as final default
- [ ] Dockerfile has no `--secret id=jfrog_user`
- [ ] `docker-compose.yml` build has `target: development`
- [ ] `docker-compose.yml` has no `jfrog_user` secret
- [ ] `docker-compose.yml` volume mounts use `/opt/venv/lib/...` not `/usr/local/lib/...`
- [ ] `pre-commit.Dockerfile` uses uv
- [ ] `pre-commit-hook` has no `jfrog_user`
- [ ] Makefile uses `uv.lock`, no `JFROG_READ_USER`
- [ ] CI workflows: no `JFROG_READ_USER`, no `jfrog_user`
- [ ] CI build_and_test uses `target: development`
- [ ] CI docker-publish uses `target: production`
- [ ] README has JFrog token instructions, no GitHub CLI instructions
- [ ] `.gitignore` updated from pipenv to uv
- [ ] No LGPL-licensed packages in prod image
