# syntax=docker/dockerfile:1
# Stage 1: Base image to install common dependencies and lock Python dependencies
# This stage is responsible for setting up the environment and installing Python packages using uv.
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20 AS python_packages

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300
ENV PIP_ROOT_USER_ACTION=ignore

# Define an argument to control whether to run uv lock (used for updating uv.lock)
ARG RUN_UV_LOCK=false
# Declare build-time arguments
ARG GITHUB_TOKEN

# Install common tools and dependencies (git is required for some Python packages)
RUN apk add --no-cache git

# Install uv from the official image (fast, single binary)
COPY --from=ghcr.io/astral-sh/uv:0.11.6@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 /uv /uvx /usr/local/bin/

# Use a venv outside the project dir so docker-compose volume mounts don't hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set the working directory inside the container
WORKDIR /usr/src/language_model_gateway

# Copy pyproject.toml and uv.lock to the working directory
COPY pyproject.toml uv.lock* /usr/src/language_model_gateway/

# Conditionally run uv lock to update the uv.lock based on the argument provided
# If RUN_UV_LOCK is true, it regenerates the uv.lock file with the latest versions of dependencies
RUN if [ "$RUN_UV_LOCK" = "true" ]; then echo "Locking dependencies" && rm -f uv.lock && uv lock --verbose; fi

# Install production dependencies only (no dev group)
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --frozen --all-extras --no-install-project --verbose

# Copy lock file for retrieval
RUN cp -f uv.lock /tmp/uv.lock

# Stage 1b: Extend the base packages with dev/test dependencies (pytest, linters, etc.)
FROM python_packages AS python_packages_dev

RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --frozen --all-extras --group dev --no-install-project --verbose


# Stage 2: Final production runtime image
# Minimal image with only production dependencies and the application code.
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20 AS production

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300

# Declare build-time arguments
ARG GITHUB_TOKEN

# Install runtime dependencies required by the application
RUN apk add --no-cache curl libstdc++ libffi git graphviz graphviz-dev

# Install uv from the official image (fast, single binary)
COPY --from=ghcr.io/astral-sh/uv:0.11.6@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 /uv /uvx /usr/local/bin/

# Set environment variables for project configuration
ENV PROJECT_DIR=/usr/src/language_model_gateway
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
ENV PIP_ROOT_USER_ACTION=ignore

# Create the directory for Prometheus metrics
RUN mkdir -p ${PROMETHEUS_MULTIPROC_DIR}

# Set the working directory for the project
WORKDIR ${PROJECT_DIR}

# Copy the venv with only production packages from the build stage
COPY --from=python_packages /opt/venv /opt/venv

# Copy pyproject.toml and uv.lock into the runtime image
COPY pyproject.toml uv.lock* ${PROJECT_DIR}/

# Copy the application code into the runtime image
COPY ./language_model_gateway ${PROJECT_DIR}/language_model_gateway

# Copy the uv.lock from the first stage
COPY --from=python_packages /usr/src/language_model_gateway/uv.lock ${PROJECT_DIR}/uv.lock
COPY --from=python_packages /tmp/uv.lock /tmp/uv.lock

# Create the folder where we will store generated images
RUN mkdir -p ${PROJECT_DIR}/image_generation
RUN mkdir -p ${PROJECT_DIR}/github_config_cache

# Expose port 5000 for the application
EXPOSE 5000

# Switch to the root user to perform user management tasks
USER root

# verify the installed version of the dot command for graphviz
RUN dot -V

# Create a restricted user (appuser) and group (appgroup) for running the application
RUN addgroup -S appgroup && adduser -S -h /etc/appuser appuser -G appgroup

# Ensure that the appuser owns the application files and directories
RUN chown -R appuser:appgroup ${PROJECT_DIR} /opt/venv ${PROMETHEUS_MULTIPROC_DIR}

# Switch to the restricted user to enhance security
USER appuser

# The number of workers can be controlled using the NUM_WORKERS environment variable
# Otherwise the number of workers for gunicorn is chosen based on these guidelines:
# (https://sentry.io/answers/number-of-uvicorn-workers-needed-in-production/)
# basically (cores * threads + 1)
#
# GUNICORN_TIMEOUT: worker timeout — kills workers that don't heartbeat within this window (default: 600s / 10 min)
CMD ["sh", "-c", "\
    CORE_COUNT=$(nproc) && \
    THREAD_COUNT=$(nproc --all) && \
    WORKER_COUNT=$((CORE_COUNT * THREAD_COUNT + 1)) && \
    FINAL_WORKERS=${NUM_WORKERS:-$WORKER_COUNT} && \
    FINAL_TIMEOUT=${GUNICORN_TIMEOUT:-600} && \
    echo \"Starting with $FINAL_WORKERS workers (cores: $CORE_COUNT, threads: $THREAD_COUNT), timeout: $FINAL_TIMEOUT\" && \
    gunicorn language_model_gateway.gateway.api:app \
        --workers $FINAL_WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:5000 \
        --timeout $FINAL_TIMEOUT \
        --log-level $(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]') \
    "]


# Stage 3: Development runtime image — extends production with dev/test dependencies and test code
FROM production AS development

USER root

# Overlay the dev venv (which is a superset of prod) on top
COPY --from=python_packages_dev /opt/venv /opt/venv

# Copy test code into the dev image
COPY ./tests ${PROJECT_DIR}/tests

# Restore ownership after the copies
RUN chown -R appuser:appgroup /opt/venv ${PROJECT_DIR}/tests

USER appuser

# Development CMD with hot reload enabled
CMD ["sh", "-c", "\
    uvicorn language_model_gateway.gateway.api:app \
        --host 0.0.0.0 \
        --port 5000 \
        --reload \
        --log-level $(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]') \
    "]


# Default stage: bare `docker build .` (no --target) produces the production image.
# Use `--target development` explicitly when dev/test dependencies are needed.
FROM production