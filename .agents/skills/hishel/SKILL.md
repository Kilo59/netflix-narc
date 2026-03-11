---
name: hishel
description: How to use the hishel caching library for Python HTTP clients
---

# Hishel Usage

Hishel is a library for HTTP caching in Python. It supports HTTPX, Requests, ASGI, FastAPI, and more.

## HTTPX Integration

Hishel provides both Synchronous and Asynchronous caching clients for HTTPX.

### Synchronous Client

```python
from hishel.httpx import SyncCacheClient
from hishel import SyncSqliteStorage

# Initialize storage backend
storage = SyncSqliteStorage(
    database_path=".csm_cache.db",
    default_ttl=7200.0, # Cache entries expire after 2 hours
)

# Initialize the SyncCacheClient with the storage
client = SyncCacheClient(
    storage=storage,
    headers={"Authorization": "Bearer token"},
    http2=True,
    timeout=10.0
)

# Use the client just like httpx.Client
response = client.get("https://api.example.com/data")
print(response.extensions.get("hishel_from_cache"))  # True or False
```

### Asynchronous Client

```python
from hishel.httpx import AsyncCacheClient
from hishel import AsyncSqliteStorage

storage = AsyncSqliteStorage(database_path=".csm_cache.db")

async with AsyncCacheClient(storage=storage) as client:
    response = await client.get("https://api.example.com/data")
```

## Storage Backends

Hishel uses `SyncSqliteStorage` and `AsyncSqliteStorage` for easy file-based persistent caching via SQLite. Do not try to instantiate an undefined `hishel.FileStorage` without verifying its exact sync/async class name. Rely on SQLite storage backends for most standard persistent caching use cases.
