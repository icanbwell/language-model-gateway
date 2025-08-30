# Pipes for installing and running in OpenWebUI

## Specifying the AWS Credentials Profile
Set `AWS_CREDENTIALS_PROFILE='{profile}'` where profile is the name of your AWS profile in docker.env

This is needed for accessing AWS Bedrock for testing.

## OpenWebUI Pipes
https://docs.openwebui.com/features/plugin/functions/pipe/

## Instructions to add pipe to OpenWebUI on local machine
- Run `make down; make up-open-webui-auth` to start OpenWebUI with authentication
  - Refer to base level README.md for instructions on setting up OAuth if you haven't already. Specifically, the keycloak host mapping in /etc/hosts.
- Login with admin/password to openwebui 
- Now run `make set-admin-user-role` to set the admin role for this new user
- Reload the OpenWebUI page in your browser
- Click top right icon and select Admin Panel
- Click Functions tab
- Click Import Functions (don’t click + to add a new function)
- Select the language_model_gateway_pipe.json file in the openwebui_functions folder in language_model_gateway 
- This contains the content of openai.py in a json string so update that if you change openai.py
- After the function has been loaded, make sure to click the toggle next to it to turn it on
- Now go back to the main UI
- There should be new models in the model dropdown

# Docker Login to pull private images from AWS ECR
`data-engineer_dev` or `admin_dev`
```shell
aws ecr get-login-password --region us-east-1 --profile {profile} | docker login --username AWS --password-stdin 875300655693.dkr.ecr.us-east-1.amazonaws.com
```

For example:
```shell
aws ecr get-login-password --region us-east-1 --profile data-engineer_dev | docker login --username AWS --password-stdin 875300655693.dkr.ecr.us-east-1.amazonaws.com
```
Or
```shell
aws ecr get-login-password --region us-east-1 --profile admin_dev | docker login --username AWS --password-stdin 875300655693.dkr.ecr.us-east-1.amazonaws.com
```
