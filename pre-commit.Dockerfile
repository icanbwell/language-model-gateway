FROM 856965016623.dkr.ecr.us-east-1.amazonaws.com/root-mirror/python:3.12-alpine3.20 AS python_packages

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300

# Install git, build-essential, and pipenv
RUN apk add --no-cache git build-base && \
    pip install pipenv

# Set the working directory
WORKDIR /sourcecode

# Copy Pipfile and Pipfile.lock
COPY Pipfile* /sourcecode

# Setup JFrog auth, install dependencies, and remove credentials
RUN --mount=type=secret,id=jfrog_user --mount=type=secret,id=jfrog_token \
    set -eu; \
    JFROG_USER=$(cat /run/secrets/jfrog_user); \
    JFROG_TOKEN=$(cat /run/secrets/jfrog_token); \
    trap 'rm -f ~/.netrc' EXIT; \
    echo "machine artifacts.bwell.com login $JFROG_USER password $JFROG_TOKEN" > ~/.netrc; \
    chmod 600 ~/.netrc; \
    pipenv sync --dev --system

# Clean up unnecessary files
RUN git config --global --add safe.directory /sourcecode

CMD ["pre-commit", "run", "--all-files"]
