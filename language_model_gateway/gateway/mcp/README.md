# MCP (Model Context Protocol) Integration

This module provides integration with MCP servers for the Language Model Gateway. It supports OAuth2 authentication and provides a robust client for interacting with MCP servers.

## Features

- **MCP Client**: Connect to MCP servers via HTTP or stdio protocols
- **OAuth2 Support**: Automatic token management with refresh capabilities
- **Manager Interface**: High-level interface for managing multiple MCP servers
- **REST API**: FastAPI router for HTTP access to MCP functionality
- **Error Handling**: Comprehensive error handling and logging
- **Async Support**: Fully asynchronous implementation

## Architecture

```
MCPManager
├── MCPClient
│   ├── OAuth2TokenManager
│   └── HTTP/WebSocket connections
└── FastAPI Router (REST API)
```

## Components

### MCPClient

The core client for interacting with MCP servers. Supports:
- Tool calling
- Resource reading
- Prompt management
- OAuth2 authentication
- Custom headers

### MCPManager

High-level manager that orchestrates multiple MCP servers:
- Server lifecycle management
- Bulk operations across servers
- Status monitoring
- Token refresh coordination

### OAuth2TokenManager

Handles OAuth2 authentication:
- Automatic token acquisition
- Token refresh with expiration handling
- Per-server token caching

## Configuration

### MCPServerConfig

```python
MCPServerConfig(
    name="my_server",
    url="https://api.example.com/mcp",
    oauth2_token_url="https://auth.example.com/oauth/token",
    oauth2_client_id="client_id",
    oauth2_client_secret="client_secret",
    oauth2_scopes=["read:tools", "execute:tools"],
    timeout=30,
    headers=[
        HeaderConfig(key="User-Agent", value="Gateway/1.0")
    ]
)
```

### Environment Variables

For OAuth2 configuration, you can use environment variables:

```bash
# Static token
EXTERNAL_API_TOKEN=your_static_token

# Dynamic OAuth2
FILE_SERVICE_CLIENT_ID=your_client_id
FILE_SERVICE_CLIENT_SECRET=your_client_secret
```

## Usage Examples

### Basic Usage

```python
from language_model_gateway.gateway.mcp import MCPManager
from language_model_gateway.configs.config_schema import MCPServerConfig

# Create manager
async with MCPManager() as manager:
    # Add server
    config = MCPServerConfig(
        name="my_server",
        url="http://localhost:8000"
    )
    await manager.add_server(config)
    
    # List tools
    tools = await manager.list_available_tools()
    
    # Call a tool
    response = await manager.call_tool(
        server_name="my_server",
        tool_name="database_query",
        arguments={"query": "SELECT * FROM users"}
    )
```

### OAuth2 Authentication

```python
# Server with OAuth2
oauth_config = MCPServerConfig(
    name="oauth_server",
    url="https://api.example.com/mcp",
    oauth2_token_url="https://auth.example.com/oauth/token",
    oauth2_client_id="your_client_id",
    oauth2_client_secret="your_client_secret",
    oauth2_scopes=["read:tools", "execute:tools"]
)

await manager.add_server(oauth_config)

# Tokens are automatically managed
response = await manager.call_tool(
    server_name="oauth_server",
    tool_name="secure_operation",
    arguments={"data": "sensitive_info"}
)
```

## REST API

The MCP functionality is exposed via REST API endpoints:

### Add Server
```http
POST /mcp/servers
Content-Type: application/json

{
    "name": "my_server",
    "url": "https://api.example.com/mcp",
    "oauth2_client_id": "client_id",
    "oauth2_client_secret": "client_secret",
    "oauth2_token_url": "https://auth.example.com/oauth/token",
    "oauth2_scopes": ["read:tools"],
    "timeout": 30
}
```

### List Tools
```http
GET /mcp/tools?server_name=my_server
```

### Call Tool
```http
POST /mcp/tools/call
Content-Type: application/json

{
    "server_name": "my_server",
    "tool_name": "database_query",
    "arguments": {
        "query": "SELECT * FROM users",
        "limit": 10
    }
}
```

### Server Status
```http
GET /mcp/servers/status
```

## Integration with Language Models

MCP servers can be integrated with language models as tools:

1. **Tool Discovery**: List available tools from configured MCP servers
2. **Dynamic Tool Calling**: Language models can call MCP tools during conversations
3. **Resource Access**: Models can read resources (files, databases, etc.) via MCP
4. **Prompt Templates**: Use MCP prompts as templates for model interactions

## Error Handling

The MCP integration includes comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Authentication Errors**: Automatic token refresh
- **Server Errors**: Graceful degradation and error reporting
- **Timeout Handling**: Configurable timeouts per server

## Security Considerations

- **OAuth2 Tokens**: Stored in memory only, automatically refreshed
- **HTTPS**: Always use HTTPS for production MCP servers
- **Secrets Management**: Use environment variables for sensitive data
- **Access Control**: Validate server configurations before adding

## Dependencies

- `mcp`: Official MCP Python package
- `aiohttp`: For HTTP client functionality
- `fastapi`: For REST API endpoints
- `pydantic`: For configuration validation

## Installation

Add to your `Pipfile`:

```toml
mcp = ">=1.0.0"
aiohttp = ">=3.10.0"
```

Then run:

```bash
pipenv install
```

## Testing

See `examples.py` for comprehensive usage examples and testing scenarios.

## Future Enhancements

- [ ] stdio:// protocol support for local MCP servers
- [ ] WebSocket support for real-time MCP interactions
- [ ] Metrics and monitoring integration
- [ ] Configuration hot-reloading
- [ ] Server health checks and circuit breakers
