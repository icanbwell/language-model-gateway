# Stage 1: Base image to install common dependencies and lock Python dependencies
# This stage is responsible for setting up the environment and installing Python packages using Pipenv.
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20 AS python_packages

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300
ENV PIP_ROOT_USER_ACTION=ignore

# Define an argument to control whether to run pipenv lock (used for updating Pipfile.lock)
ARG RUN_PIPENV_LOCK=false
# Declare build-time arguments
ARG GITHUB_TOKEN

# Install common tools and dependencies (git is required for some Python packages)
RUN apk add --no-cache git

# Install pipenv, a tool for managing Python project dependencies
RUN pip install pipenv

# Set the working directory inside the container
WORKDIR /usr/src/language_model_gateway

# Copy Pipfile and Pipfile.lock to the working directory
# Pipfile defines the Python packages required for the project
# Pipfile.lock ensures consistency by locking the exact versions of packages
COPY Pipfile* /usr/src/language_model_gateway/

# Show the current pip configuration (for debugging purposes)
RUN pip config list

# Conditionally run pipenv lock to update the Pipfile.lock based on the argument provided
# If RUN_PIPENV_LOCK is true, it regenerates the Pipfile.lock file with the latest versions of dependencies
RUN if [ "$RUN_PIPENV_LOCK" = "true" ]; then echo "Locking Pipfile" && rm -f Pipfile.lock && pipenv lock --dev --clear --verbose --extra-pip-args="--prefer-binary"; fi

# Install all dependencies using the locked versions in Pipfile.lock
# --dev installs development dependencies, --system installs them globally in the container's Python environment
RUN pipenv sync --dev --system --verbose --extra-pip-args="--prefer-binary"

# Create necessary directories and list their contents (for debugging and verification)
RUN mkdir -p /usr/local/lib/python3.12/site-packages && ls -halt /usr/local/lib/python3.12/site-packages
RUN mkdir -p /usr/local/bin && ls -halt /usr/local/bin

# Check and print system and Python platform information (for debugging)
RUN python -c "import platform; print(platform.platform()); print(platform.architecture())"
RUN python -c "import sys; print(sys.platform, sys.version, sys.maxsize > 2**32)"

# Debug pip installation and list installed packages with verbosity
RUN pip debug --verbose
RUN pip list -v


# Stage 2: Development image with hot reload
# This stage is optimized for local development with hot reload capability
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20 AS development

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300

# Define an argument to control whether to run pipenv lock (not used in this stage)
ARG GITHUB_TOKEN

# Install runtime dependencies required by the application
RUN apk add --no-cache curl libstdc++ libffi git graphviz graphviz-dev

# Install pipenv to manage and run the application
RUN pip install --no-cache-dir pipenv

# Set environment variables for project configuration
ENV PROJECT_DIR=/usr/src/language_model_gateway
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
ENV PIP_ROOT_USER_ACTION=ignore

# Create the directory for Prometheus metrics
RUN mkdir -p ${PROMETHEUS_MULTIPROC_DIR}

# Set the working directory for the project
WORKDIR ${PROJECT_DIR}

# Copy the Pipfile and Pipfile.lock files into the development image
COPY Pipfile* ${PROJECT_DIR}

# Copy installed Python packages from the first stage
COPY --from=python_packages /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python_packages /usr/local/bin /usr/local/bin

# Copy the application code into the development image
COPY ./language_model_gateway ${PROJECT_DIR}/language_model_gateway
COPY ./setup.cfg ${PROJECT_DIR}/

# Copy the Pipfile.lock from the first stage
COPY --from=python_packages ${PROJECT_DIR}/Pipfile.lock ${PROJECT_DIR}/Pipfile.lock
COPY --from=python_packages ${PROJECT_DIR}/Pipfile.lock /tmp/Pipfile.lock

# Create directories and list their contents (for debugging and verification)
RUN mkdir -p /usr/local/lib/python3.12/site-packages && ls -halt /usr/local/lib/python3.12/site-packages
RUN mkdir -p /usr/local/bin && ls -halt /usr/local/bin

# Create the folder where we will store generated images
RUN mkdir -p ${PROJECT_DIR}/image_generation

# Install the dependencies using pipenv in the development environment
RUN pipenv sync --dev --system --extra-pip-args="--prefer-binary"

# Expose port 5000 for the application
EXPOSE 5000

# Switch to the root user to perform user management tasks
USER root

# verify the installed version of the dot command for graphviz
RUN dot -V

# Create a restricted user (appuser) and group (appgroup) for running the application
RUN addgroup -S appgroup && adduser -S -h /etc/appuser appuser -G appgroup

# Ensure that the appuser owns the application files and directories
RUN chown -R appuser:appgroup ${PROJECT_DIR} /usr/local/lib/python3.12/site-packages /usr/local/bin ${PROMETHEUS_MULTIPROC_DIR}

# Switch to the restricted user to enhance security
USER appuser

# Development CMD with hot reload enabled
CMD ["sh", "-c", "\
    uvicorn language_model_gateway.gateway.api:app \
        --host 0.0.0.0 \
        --port 5000 \
        --reload \
        --log-level $(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]') \
    "]

# Stage 3: Production deployment image
# This stage is optimized for deployment with multiple workers
FROM public.ecr.aws/docker/library/python:3.12-alpine3.20 AS production

# Set terminal width (COLUMNS) and height (LINES)
ENV COLUMNS=300

# Define an argument to control whether to run pipenv lock (not used in this stage)
ARG GITHUB_TOKEN

# Install runtime dependencies required by the application
RUN apk add --no-cache curl libstdc++ libffi git graphviz graphviz-dev

# Install pipenv to manage and run the application
RUN pip install --no-cache-dir pipenv

# Set environment variables for project configuration
ENV PROJECT_DIR=/usr/src/language_model_gateway
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
ENV PIP_ROOT_USER_ACTION=ignore

# Create the directory for Prometheus metrics
RUN mkdir -p ${PROMETHEUS_MULTIPROC_DIR}

# Set the working directory for the project
WORKDIR ${PROJECT_DIR}

# Copy the Pipfile and Pipfile.lock files into the development image
COPY Pipfile* ${PROJECT_DIR}

# Copy installed Python packages from the first stage
COPY --from=python_packages /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python_packages /usr/local/bin /usr/local/bin

# Copy the application code into the development image
COPY ./language_model_gateway ${PROJECT_DIR}/language_model_gateway
COPY ./setup.cfg ${PROJECT_DIR}/

# Copy the Pipfile.lock from the first stage
COPY --from=python_packages ${PROJECT_DIR}/Pipfile.lock ${PROJECT_DIR}/Pipfile.lock
COPY --from=python_packages ${PROJECT_DIR}/Pipfile.lock /tmp/Pipfile.lock

# Create directories and list their contents (for debugging and verification)
RUN mkdir -p /usr/local/lib/python3.12/site-packages && ls -halt /usr/local/lib/python3.12/site-packages
RUN mkdir -p /usr/local/bin && ls -halt /usr/local/bin

# Create the folder where we will store generated images
RUN mkdir -p ${PROJECT_DIR}/image_generation

# Install the dependencies using pipenv in the development environment
RUN pipenv sync --dev --system --extra-pip-args="--prefer-binary"

# Expose port 5000 for the application
EXPOSE 5000

# Switch to the root user to perform user management tasks
USER root

# verify the installed version of the dot command for graphviz
RUN dot -V

# Create a restricted user (appuser) and group (appgroup) for running the application
RUN addgroup -S appgroup && adduser -S -h /etc/appuser appuser -G appgroup

# Ensure that the appuser owns the application files and directories
RUN chown -R appuser:appgroup ${PROJECT_DIR} /usr/local/lib/python3.12/site-packages /usr/local/bin ${PROMETHEUS_MULTIPROC_DIR}

# Switch to the restricted user to enhance security
USER appuser

# The number of workers can be controlled using the NUM_WORKERS environment variable
# Otherwise the number of workers for uvicorn (using the multiprocessing worker) is chosen based on these guidelines:
# (https://sentry.io/answers/number-of-uvicorn-workers-needed-in-production/)
# basically (cores * threads + 1)
CMD ["sh", "-c", "\
    # Get CPU info \
    CORE_COUNT=$(nproc) && \
    THREAD_COUNT=$(nproc --all) && \
    \
    # Calculate workers using formula: (cores * threads + 1) \
    WORKER_COUNT=$((CORE_COUNT * THREAD_COUNT + 1)) && \
    FINAL_WORKERS=${NUM_WORKERS:-$WORKER_COUNT} && \
    \
    # Log the configuration \
    echo \"Starting with $FINAL_WORKERS workers (cores: $CORE_COUNT, threads: $THREAD_COUNT)\" && \
    \
    # Start the application \
    uvicorn language_model_gateway.gateway.api:app \
        --host 0.0.0.0 \
        --port 5000 \
        --workers $FINAL_WORKERS \
        --log-level $(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]') \
    "]