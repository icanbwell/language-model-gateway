FROM public.ecr.aws/docker/library/python:3.12-alpine3.20

# Update and install necessary packages
RUN apk update

RUN pip install --upgrade pip

RUN pip install python-keycloak requests

# Create a non-root user and set permissions
RUN adduser -D appuser
WORKDIR /home/appuser
RUN mkdir -p /config && chown appuser:appuser /config

# Switch to non-root user
USER appuser

# Test: show Python version (uncomment for debugging)
# RUN python --version

#RUN python /config/keycloak_config.py