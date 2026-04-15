# Pipes for installing and running in OpenWebUI

## Specifying the AWS Credentials Profile
Set `AWS_CREDENTIALS_PROFILE='{profile}'` where profile is the name of your AWS profile in .env

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
- Select the language_model_gateway_pipe.json file in the openwebui-config/functions folder in language_model_gateway 
- This contains the content of openai.py in a json string so update that if you change openai.py
- After the function has been loaded, make sure to click the toggle next to it to turn it on
- Now go back to the main UI
- There should be new models in the model dropdown

## MCP Apps Support

The pipe supports rendering MCP Apps — interactive HTML UIs returned by MCP tools that declare a `ui://` resource. When the LLM backend calls such a tool, the HTML is streamed back as a custom `event: mcp_app` SSE event.

**How it works:**

1. The LLM backend (language-model-gateway API) detects the `ui://` resource on the tool, fetches the HTML, and emits it as a named SSE event: `event: mcp_app\ndata: {"html": "...", "title": "..."}\n\n`
2. The pipe's SSE parser recognizes named events and routes `mcp_app` events to the embed handler
3. The handler emits the HTML to OpenWebUI via `__event_emitter__({"type": "embeds", "data": {"embeds": [html]}})`
4. OpenWebUI renders the HTML in a sandboxed iframe with auto-height sizing

**Configuration:**

The pipe valve `mcp_app_event_name` (default: `mcp_app`) controls which SSE event name triggers embed emission. No other configuration is needed.

**Requirements:**

- The MCP server must declare `meta.ui.resourceUri` on tools and implement `resources/read` for the URI
- The `language-model-common` library must be v2+ (includes MCP Apps support)
- OpenWebUI must support the `embeds` event type (standard in recent versions)

For full architecture details, see [language-model-common/docs/mcp-apps.md](../../language-model-common/docs/mcp-apps.md) (relative path from this repo — refer to the language-model-common project).

---

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
