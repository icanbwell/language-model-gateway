---
name: setup-jfrog-auth
description: Walk a developer through one-time machine setup for JFrog Artifactory and AWS ECR authentication at bwell. Generates JFrog Identity Token, configures shell environment variables, sets up ECR login, and optionally configures per-tool credential files (~/.netrc for pipenv/pip, ~/.npmrc for npm, ~/.gradle/gradle.properties for Gradle). Does NOT cover per-project migration — use migrate-pipenv-to-uv for that.
when_to_use: When a developer needs to set up JFrog auth on their machine, get a JFrog token, configure JFROG_READ_USER/JFROG_READ_TOKEN, set up ECR login for Docker base images, or troubleshoot 401 errors from JFrog/ECR.
disable-model-invocation: true
user-invocable: true
allowed-tools: Read Write Edit Bash Grep Glob
effort: low
---

# Set Up JFrog & ECR Authentication (One-Time Machine Setup)

You are helping a developer configure their local machine to authenticate with bwell's JFrog Artifactory (for package registries) and AWS ECR (for hardened Docker base images).

This is a **one-time machine setup**. Per-project Dockerfile/docker-compose/CI changes are handled by the `migrate-pipenv-to-uv` skill and the rootio-terraform migration guide.

## Reference

- Migration guide: https://icanbwell.atlassian.net/wiki/x/CoBIcQE
- Sample repo: https://github.com/icanbwell/rootio-terraform

## Before starting

Check what the developer already has configured:

```bash
# Check for existing JFrog env vars
grep -n 'JFROG_READ' ~/.zshrc ~/.bashrc 2>/dev/null || echo "No JFrog vars found in shell config"

# Check for existing .netrc
test -f ~/.netrc && grep 'artifacts.bwell.com' ~/.netrc && echo ".netrc exists" || echo "No .netrc for JFrog"

# Check for existing ECR alias
grep -n 'ecr-login\|ecr.*get-login' ~/.zshrc ~/.bashrc 2>/dev/null || echo "No ECR alias found"

# Check AWS CLI
which aws && aws --version || echo "AWS CLI not installed"

# Check Docker
which docker && docker --version || echo "Docker not installed"
```

Skip any step where configuration already exists and is correct.

---

## Step 1: Generate JFrog Identity Token

Tell the developer:

> 1. Log in to **https://artifacts.bwell.com/** using your bwell SSO credentials
> 2. Click your **profile icon** (top-right) → **Edit Profile**
> 3. In the **Identity Tokens** section, click **Generate Token**
> 4. Name it something descriptive (e.g., `local-dev`)
> 5. Click **Generate** and **copy the token immediately** — it will not be shown again

The developer's JFrog username is their bwell email (e.g., `you@bwell.zone`).

---

## Step 2: Add JFrog credentials to shell profile

Add to `~/.zshrc` (or `~/.bashrc` if they use bash):

```bash
# bwell JFrog Artifactory credentials
export JFROG_READ_USER=<their-email>@bwell.zone
export JFROG_READ_TOKEN=<their-token>
```

Then reload:

```bash
source ~/.zshrc
```

Verify:

```bash
echo "User: $JFROG_READ_USER"
echo "Token set: $([ -n "$JFROG_READ_TOKEN" ] && echo 'yes' || echo 'NO')"
```

**Important**: Ask the developer for their bwell email. Do NOT guess or hardcode it. For the token, instruct them to paste it — never log or echo the actual token value.

---

## Step 3: Set up AWS ECR login

bwell uses hardened Docker base images from an internal ECR mirror at:
```
856965016623.dkr.ecr.us-east-1.amazonaws.com/root-mirror
```

### Prerequisites

- AWS CLI installed (`brew install awscli` on macOS)
- An AWS profile configured with access to the services account (856965016623)
- If not set up, direct them to the **AWS Access bwell via Okta — Quick Start Guide**

### Add ECR login alias

Ask which AWS profile name they use for the services account (common names: `admin_services`, `services`). Add to `~/.zshrc`:

```bash
# ECR login for bwell hardened base images (token valid 12 hours)
alias ecr-login='aws ecr get-login-password --region us-east-1 --profile <their-profile> | docker login --username AWS --password-stdin 856965016623.dkr.ecr.us-east-1.amazonaws.com'
```

Then reload and test:

```bash
source ~/.zshrc
ecr-login
```

A successful login prints: `Login Succeeded`

---

## Step 4: Configure per-tool credentials (optional)

Only needed if the developer runs package managers **outside of Docker** (e.g., for IDE support, local testing). Ask which languages they work with.

### Python (pipenv/pip) — ~/.netrc

```bash
# Add JFrog auth for pipenv/pip
echo "machine artifacts.bwell.com login $JFROG_READ_USER password $JFROG_READ_TOKEN" >> ~/.netrc
chmod 600 ~/.netrc
```

Verify:

```bash
cat ~/.netrc | grep artifacts.bwell.com | sed "s/password .*/password ***REDACTED***/"
ls -la ~/.netrc  # should show -rw-------
```

### Python (uv) — environment variables only

uv reads credentials from environment variables. No extra file config needed if Step 2 is done. The per-project `pyproject.toml` maps the index name to env vars:

```
UV_INDEX_JFROG_USERNAME  →  $JFROG_READ_USER (or empty string for token-only auth)
UV_INDEX_JFROG_PASSWORD  →  $JFROG_READ_TOKEN
```

### Node.js — project-level .npmrc

Node.js uses a per-project `.npmrc` that references the env var. No global config needed — the project's `.npmrc.example` template is copied:

```bash
# In each Node.js project:
cp .npmrc.example .npmrc
```

The `.npmrc` contains `${JFROG_READ_TOKEN}` which npm interpolates from the environment (set in Step 2).

### Java (Gradle) — ~/.gradle/gradle.properties

```bash
mkdir -p ~/.gradle

# Check if properties already exist
grep -q 'jfrogUser' ~/.gradle/gradle.properties 2>/dev/null && echo "Already configured" || {
    echo "jfrogUser=$JFROG_READ_USER" >> ~/.gradle/gradle.properties
    echo "jfrogToken=$JFROG_READ_TOKEN" >> ~/.gradle/gradle.properties
    echo "Added JFrog credentials to ~/.gradle/gradle.properties"
}
```

**Warning**: Never commit `gradle.properties` files containing credentials.

---

## Step 5: Verify everything works

Run these checks:

```bash
echo "=== JFrog Environment ==="
[ -n "$JFROG_READ_USER" ] && echo "✓ JFROG_READ_USER is set" || echo "✗ JFROG_READ_USER is NOT set"
[ -n "$JFROG_READ_TOKEN" ] && echo "✓ JFROG_READ_TOKEN is set" || echo "✗ JFROG_READ_TOKEN is NOT set"

echo ""
echo "=== AWS CLI ==="
which aws > /dev/null 2>&1 && echo "✓ AWS CLI installed: $(aws --version 2>&1 | head -1)" || echo "✗ AWS CLI not found"

echo ""
echo "=== Docker ==="
which docker > /dev/null 2>&1 && echo "✓ Docker installed: $(docker --version)" || echo "✗ Docker not found"

echo ""
echo "=== ECR Login Alias ==="
grep -q 'ecr-login' ~/.zshrc 2>/dev/null && echo "✓ ecr-login alias configured" || echo "✗ ecr-login alias not found in ~/.zshrc"
```

### Test JFrog connectivity (pick one based on their language)

**Python**:
```bash
pip index versions flask --index-url https://$JFROG_READ_USER:$JFROG_READ_TOKEN@artifacts.bwell.com/artifactory/api/pypi/virtual-pypi/simple 2>&1 | head -3
```

**Node.js** (with JFROG_READ_TOKEN set):
```bash
npm view express version --registry https://artifacts.bwell.com/artifactory/api/npm/virtual-npm/
```

**Java**:
```bash
./gradlew dependencies 2>&1 | tail -5
```

---

## JFrog Registry URLs Reference

| Language | JFrog Virtual Registry URL | Auth Method |
|----------|---------------------------|-------------|
| Python   | `https://artifacts.bwell.com/artifactory/api/pypi/virtual-pypi/simple` | `.netrc` or env vars |
| Node.js  | `https://artifacts.bwell.com/artifactory/api/npm/virtual-npm/` | `.npmrc` with `${JFROG_READ_TOKEN}` |
| Java     | `https://artifacts.bwell.com/artifactory/virtual-maven/` | `gradle.properties` or env vars |

These virtual registries resolve from root.io's hardened library first, then fall back to the standard upstream (PyPI / npmjs / Maven Central).

---

## Troubleshooting

### 401 Unauthorized from JFrog

- Verify env vars are set: `echo $JFROG_READ_USER` / `echo ${JFROG_READ_TOKEN:+set}`
- Token may have expired — regenerate at https://artifacts.bwell.com/ → Edit Profile → Identity Tokens
- For pipenv: check `~/.netrc` exists with correct format and `chmod 600` permissions
- For npm: check `.npmrc` uses `${JFROG_READ_TOKEN}` (not a hardcoded value)

### ECR pull access denied

- ECR tokens expire after **12 hours** — re-run `ecr-login`
- Verify AWS profile has access to account `856965016623`
- Check available image tags:
  ```bash
  aws ecr describe-images --repository-name root-mirror/python --region us-east-1 --query 'imageDetails[*].imageTags' --output table
  ```

### "secret not found" during Docker build

- Ensure `.env` file exists in the project root with `JFROG_READ_USER` and `JFROG_READ_TOKEN`
- Ensure `docker-compose.yaml` has a `secrets:` section mapping the env vars
- Docker BuildKit must be enabled (Docker 18.09+)

### Security reminders

- **Never commit**: `.env`, `.envrc`, `.netrc`, `.npmrc`, `gradle.properties` (with creds)
- **Never use `ARG` or `ENV`** for secrets in Dockerfiles — always use `--mount=type=secret`
- **Always `chmod 600 ~/.netrc`** — pip warns if world-readable
