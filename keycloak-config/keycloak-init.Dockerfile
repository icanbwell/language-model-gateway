FROM public.ecr.aws/docker/library/python:3.12-alpine3.20

# Update and install necessary packages
RUN apk update

RUN pip install --upgrade pip

RUN pip install python-keycloak requests

#RUN python /config/keycloak_config.py