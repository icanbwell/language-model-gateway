# syntax=docker/dockerfile:1
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300

ARG GITHUB_TOKEN

# Install git, build-essential, and uv
RUN apk add --no-cache git build-base
# Install uv from the official image (fast, single binary)
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --frozen --all-extras --no-install-project

# Set the working directory
WORKDIR /sourcecode

# Clean up unnecessary files
RUN git config --global --add safe.directory /sourcecode

CMD ["pre-commit", "run", "--all-files"]
