# Caching in Language Model Gateway

This document provides a comprehensive overview of where and how caching is implemented in the Language Model Gateway project.

## Table of Contents

1. [Overview](#overview)
2. [Model Configuration Caching](#model-configuration-caching)
3. [Token/Authentication Caching](#tokenauthentication-caching)
4. [MCP Tools Metadata Caching](#mcp-tools-metadata-caching)
5. [Simple Function Caching](#simple-function-caching)
6. [Cache-Related Environment Variables](#cache-related-environment-variables)
7. [Implementation Details](#implementation-details)

---

## Overview

The Language Model Gateway uses several caching mechanisms to improve performance and reduce redundant operations:

1. **Model Configuration Caching** - Caches model configurations to avoid repeatedly reading from disk/S3/GitHub
2. **Token/Authentication Caching** - Stores OAuth tokens in MongoDB to enable token reuse and exchange
3. **MCP Tools Metadata Caching** - Caches MCP (Model Context Protocol) tool metadata
4. **Simple Function Caching** - A decorator-based caching utility for async functions

---

## Model Configuration Caching

### Location
- **Implementation**: `language_model_gateway/gateway/utilities/cache/config_expiring_cache.py`
- **Usage**: `language_model_gateway/configs/config_reader/config_reader.py`
- **Base Class**: `language_model_gateway/gateway/utilities/cache/expiring_cache.py`

### Description
The `ConfigExpiringCache` is a time-based expiring cache that stores model configurations (`List[ChatModelConfig]`). It prevents the system from repeatedly reading model configuration files from various sources (local filesystem, S3, GitHub).

### Key Features
- **TTL-based expiration**: Configurations expire after a configurable time period
- **Thread-safe**: Uses `asyncio.Lock` for safe concurrent access
- **Double-check locking**: Prevents multiple simultaneous loads of the same configuration
- **Singleton pattern**: Only one instance exists across the application

### Configuration
```python
# Environment variable (defaults to 3600 seconds / 1 hour)
CONFIG_CACHE_TIMEOUT_SECONDS=3600
```

### How It Works
1. When model configurations are requested, the cache is checked first
2. If cached and valid (not expired), cached data is returned immediately
3. If cache is invalid/empty, configurations are loaded from source
4. The loaded configurations are stored in cache with a timestamp
5. Cache automatically invalidates after TTL expires

### Registration
The cache is registered as a singleton in the dependency injection container:
```python
# In container_factory.py
container.singleton(
    ConfigExpiringCache,
    lambda c: ConfigExpiringCache(
        ttl_seconds=(
            int(os.environ["CONFIG_CACHE_TIMEOUT_SECONDS"])
            if os.environ.get("CONFIG_CACHE_TIMEOUT_SECONDS")
            else 60 * 60  # Default: 1 hour
        )
    )
)
```

### Methods
- `is_valid()` - Check if cache is still valid based on TTL
- `get()` - Retrieve cached value if valid
- `set(value)` - Store new value and update timestamp
- `clear()` - Clear the cache
- `create(init_value)` - Initialize cache with optional value

---

## Token/Authentication Caching

### Location
- **Model**: `language_model_gateway/gateway/auth/models/token_cache_item.py`
- **Manager**: `language_model_gateway/gateway/auth/token_exchange/token_exchange_manager.py`
- **Storage**: MongoDB collection (configurable via environment variable)

### Description
The `TokenCacheItem` model represents cached OAuth tokens stored in MongoDB. This enables token reuse across requests and token exchange operations.

### Key Features
- **Persistent storage**: Tokens are stored in MongoDB for durability
- **Multiple token types**: Supports access tokens, ID tokens, and refresh tokens
- **Token validation**: Built-in methods to check token validity
- **Subject tracking**: Links tokens to referring subjects for token exchange
- **Provider tracking**: Associates tokens with specific auth providers

### Token Cache Item Structure
```python
class TokenCacheItem(BaseDbModel):
    created: datetime              # Creation timestamp
    updated: Optional[datetime]    # Last update timestamp
    refreshed: Optional[datetime]  # Last refresh timestamp
    auth_provider: str            # Authentication provider (e.g., "google", "github")
    client_id: Optional[str]      # OAuth client ID
    issuer: str | None            # Token issuer
    audience: str                 # Intended audience
    email: Optional[str]          # User email
    subject: str                  # User subject/ID
    referring_email: Optional[str] # Original token's email
    referring_subject: str        # Original token's subject
    referrer: Optional[str]       # Associated URL
    access_token: Optional[Token] # Access token
    id_token: Optional[Token]     # ID token
    refresh_token: Optional[Token] # Refresh token
```

### Configuration
```bash
# MongoDB connection for token storage
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=language_model_gateway
MONGO_DB_TOKEN_COLLECTION_NAME=tokens

# Cache type (mongodb, memory, etc.)
OAUTH_CACHE=mongodb
```

### How It Works
1. When a user authenticates, tokens are stored in MongoDB
2. Tokens are indexed by `auth_provider` and `referring_subject`
3. When making API calls that require authentication:
   - The system checks MongoDB for existing valid tokens
   - If found and valid, the cached token is reused
   - If expired but refresh token exists, token is refreshed
   - If no valid token exists, re-authentication is required
4. Tokens are validated based on expiration times

### Token Exchange Flow
The `TokenExchangeManager` handles:
- Storing new tokens after authentication
- Retrieving tokens for specific auth providers and subjects
- Checking token validity
- Managing token refresh operations

---

## MCP Tools Metadata Caching

### Location
- **Usage**: `language_model_gateway/gateway/mcp/mcp_tool_provider.py`
- **Environment Variables**: `language_model_gateway/gateway/utilities/language_model_gateway_environment_variables.py`

### Description
MCP (Model Context Protocol) tools metadata is cached to avoid repeatedly fetching tool definitions from MCP servers.

### Configuration
```bash
# Cache timeout in seconds (default: 3600 = 1 hour)
MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS=3600

# Cache TTL in seconds (default: 3600 = 1 hour)
MCP_TOOLS_METADATA_CACHE_TTL_SECONDS=3600
```

### Environment Variables
```python
@property
def mcp_tools_metadata_cache_timeout_seconds(self) -> int:
    return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS", 3600))

@property
def mcp_tools_metadata_cache_ttl_seconds(self) -> int:
    return int(os.environ.get("MCP_TOOLS_METADATA_CACHE_TTL_SECONDS", 3600))
```

### How It Works
1. MCP tool metadata (available tools, their schemas, etc.) is fetched from MCP servers
2. This metadata is cached for the configured duration
3. Subsequent requests for tool metadata use the cached version
4. Cache expires after the TTL period, triggering a fresh fetch

---

## Simple Function Caching

### Location
- **Implementation**: `language_model_gateway/gateway/utilities/cached.py`

### Description
A simple decorator that caches the result of an async function. The cached value is stored in memory and persists for the lifetime of the application.

### Implementation
```python
def cached(f: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Decorator to cache the result of an async function"""
    cache: R | None = None

    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal cache
        
        if cache is not None:
            return cache
        
        cache = await f(*args, **kwargs)
        return cache
    
    return wrapper
```

### Usage
```python
from language_model_gateway.gateway.utilities.cached import cached

@cached
async def expensive_operation() -> Result:
    # This will only execute once
    # Subsequent calls return the cached result
    return await perform_expensive_operation()
```

### Characteristics
- **One-time execution**: Function is only executed once, then cached forever
- **No expiration**: Cache persists for application lifetime
- **No cache key**: Cannot cache different results for different arguments
- **Memory-based**: Stored in process memory
- **Simple use case**: Best for initialization or setup operations that never change

---

## Cache-Related Environment Variables

### Configuration Cache
```bash
# Model configuration cache TTL (default: 3600 seconds)
CONFIG_CACHE_TIMEOUT_SECONDS=3600
```

### Token/Auth Cache
```bash
# MongoDB settings for token storage
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=language_model_gateway
MONGO_DB_TOKEN_COLLECTION_NAME=tokens

# Cache type selection
OAUTH_CACHE=mongodb
```

### MCP Tools Cache
```bash
# MCP tools metadata cache settings (default: 3600 seconds each)
MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS=3600
MCP_TOOLS_METADATA_CACHE_TTL_SECONDS=3600
```

---

## Implementation Details

### Expiring Cache Pattern

All TTL-based caches follow a common pattern defined by the `ExpiringCache` abstract base class:

```python
class ExpiringCache[T](ABC):
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if cache is valid (not expired)"""
        pass
    
    @abstractmethod
    async def get(self) -> Optional[T]:
        """Get cached value if valid"""
        pass
    
    @abstractmethod
    async def set(self, value: T) -> None:
        """Set new cached value"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear the cache"""
        pass
    
    @abstractmethod
    async def create(self, *, init_value: Optional[T] = None) -> Optional[T]:
        """Initialize cache"""
        pass
```

### Thread Safety

The `ConfigExpiringCache` uses `asyncio.Lock` to ensure thread-safe operations:

```python
_lock: asyncio.Lock = asyncio.Lock()

async def set(self, value: List[ChatModelConfig]) -> None:
    async with self._lock:
        self._cache = value
        self._cache_timestamp = time.time()
```

### Double-Check Locking

The `ConfigReader` uses double-check locking to prevent multiple simultaneous loads:

```python
# First check (without lock)
cached_configs = await self._cache.get()
if cached_configs is not None:
    return cached_configs

# Acquire lock
async with self._lock:
    # Second check (with lock)
    cached_configs = await self._cache.get()
    if cached_configs is not None:
        return cached_configs
    
    # Load configurations
    models = await self.read_models_from_path_async(config_path)
    await self._cache.set(models)
    return models
```

This pattern ensures:
1. Fast path for cached data (no lock contention)
2. Only one thread loads data if cache is empty
3. Other threads wait and reuse the loaded data

---

## Summary

The Language Model Gateway implements caching at multiple levels:

1. **Model Configurations**: Time-based expiring cache (1 hour default) to avoid repeated file reads
2. **OAuth Tokens**: Persistent MongoDB storage for token reuse and exchange
3. **MCP Tool Metadata**: Time-based cache (1 hour default) to reduce MCP server requests
4. **Function Results**: Simple decorator-based caching for one-time operations

These caching mechanisms significantly improve performance by:
- Reducing disk/network I/O operations
- Enabling token reuse across requests
- Minimizing redundant API calls to external services
- Speeding up application startup and request handling

All caches are configurable via environment variables, allowing operators to tune cache behavior based on their specific requirements.
