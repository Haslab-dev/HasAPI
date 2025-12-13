"""
HasAPI with Bun Accelerators

This example shows how to use Bun for specific tasks while
keeping Python as the main framework.

Architecture:
    Client → Bun Gateway (8080) → Python API (8000)
                ↓
         - Rate limiting
         - API key validation  
         - Health checks (no Python)
         - TLS termination

Python handles all business logic with full pip compatibility.
Bun handles edge concerns without IPC overhead.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from hasapi.fast import FastAPI
from hasapi.accelerators import BunGateway, BunCache, BunStreamServer
from hasapi.accelerators.gateway import GatewayConfig, RateLimitConfig
from hasapi.accelerators.cache import CacheConfig, CacheRule
from hasapi.accelerators.stream import StreamConfig


# Create Python API (runs on port 8000)
app = FastAPI(docs=True)


@app.get("/")
async def index(request):
    """Main endpoint - handled by Python"""
    return {"message": "Hello from Python!", "framework": "HasAPI"}


@app.get("/users/{user_id}")
async def get_user(request):
    """User endpoint - handled by Python, cached by Bun"""
    user_id = request.path_params.get("user_id")
    # Simulate database query
    await asyncio.sleep(0.01)
    return {"user_id": user_id, "name": f"User {user_id}"}


@app.get("/slow")
async def slow_endpoint(request):
    """Slow endpoint - Python handles, Bun protects with rate limiting"""
    await asyncio.sleep(0.5)
    return {"status": "completed"}


@app.post("/ai/inference")
async def ai_inference(request):
    """AI inference - full Python, any pip library works"""
    # You can use PyTorch, transformers, etc. here
    # import torch
    # import transformers
    return {"prediction": [0.1, 0.9], "model": "example"}


async def main():
    """
    Start Python API + Bun accelerators
    
    Traffic flow:
    1. Client connects to Gateway (8080)
    2. Gateway handles: rate limiting, auth, health checks
    3. Valid requests forwarded to Python (8000)
    4. Cache intercepts cacheable responses
    5. Stream server handles WebSocket separately (8082)
    """
    
    # 1. Start Bun Gateway (edge proxy)
    gateway = BunGateway(GatewayConfig(
        host='0.0.0.0',
        port=8080,
        backend_host='127.0.0.1',
        backend_port=8000,
        
        # Rate limiting: 100 req/s per IP
        rate_limit=RateLimitConfig(
            requests_per_second=100,
            burst=200,
        ),
        
        # Static responses (no Python needed)
        static_routes={
            '/health': {'status': 'healthy'},
            '/version': {'version': '1.0.0', 'engine': 'hasapi'},
        },
        
        # API key validation (optional)
        # require_api_key=True,
        # valid_api_keys=['key1', 'key2'],
        
        # Load shedding
        max_concurrent=1000,
    ))
    
    # 2. Start Bun Cache (optional)
    cache = BunCache(CacheConfig(
        host='127.0.0.1',
        port=8083,
        backend_host='127.0.0.1',
        backend_port=8000,
        rules=[
            CacheRule('/users/*', ttl=60),  # Cache user data for 60s
            CacheRule('/api/products/*', ttl=300),  # Cache products for 5min
        ],
    ))
    
    # 3. Start Bun Stream Server (WebSocket/SSE)
    stream = BunStreamServer(StreamConfig(
        host='0.0.0.0',
        port=8082,
        max_connections=10000,
    ))
    
    print("\n" + "=" * 60)
    print("HasAPI with Bun Accelerators")
    print("=" * 60)
    
    try:
        # Start accelerators
        await gateway.start()
        # await cache.start()  # Uncomment to enable caching
        # await stream.start()  # Uncomment to enable WebSocket
        
        print("\n📍 Endpoints:")
        print("   Gateway:    http://localhost:8080  (rate limited, protected)")
        print("   Python API: http://localhost:8000  (direct, for testing)")
        print("   WebSocket:  ws://localhost:8082   (if enabled)")
        print("\n📊 Static routes (no Python):")
        print("   GET /health  → instant response from Bun")
        print("   GET /version → instant response from Bun")
        print("\n🐍 Python routes (full pip compatibility):")
        print("   GET /        → Python handler")
        print("   GET /users/* → Python + optional cache")
        print("   POST /ai/*   → Python (PyTorch, etc.)")
        print("\n" + "=" * 60)
        
        # Start Python server (blocking)
        app.run(host='127.0.0.1', port=8000, engine='python')
        
    finally:
        await gateway.stop()
        # await cache.stop()
        # await stream.stop()


if __name__ == "__main__":
    asyncio.run(main())
