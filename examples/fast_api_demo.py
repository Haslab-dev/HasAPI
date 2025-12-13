"""
HasAPI Fast Demo

Demonstrates the high-performance FastAPI implementation.

Run with:
    python examples/fast_api_demo.py

Or with specific engine:
    HASAPI_ENGINE=python python examples/fast_api_demo.py
"""

import sys
sys.path.insert(0, '.')

from hasapi import FastAPI, FastRequest, FastJSONResponse

# Create app with auto-detected engine
# - Unix: Native (Bun) by default, or Python with HASAPI_ENGINE=python
# - Windows: Python (uvloop + httptools)
app = FastAPI(
    title="HasAPI Fast Demo",
    version="1.0.0",
    docs=True
)


@app.get("/")
async def index(request: FastRequest):
    """Root endpoint - returns welcome message"""
    return {"message": "Welcome to HasAPI Fast!", "version": "1.0.0"}


@app.get("/json")
async def json_endpoint(request: FastRequest):
    """JSON endpoint - returns complex JSON for benchmarking"""
    return {
        "message": "Hello, World!",
        "items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "nested": {
            "key": "value",
            "numbers": [1.1, 2.2, 3.3],
            "deep": {"level": 3}
        },
        "unicode": "こんにちは世界 🌍"
    }


@app.get("/users/{user_id}")
async def get_user(request: FastRequest):
    """Get user by ID - demonstrates path parameters"""
    user_id = request.path_params.get("user_id")
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }


@app.post("/users")
async def create_user(request: FastRequest):
    """Create user - demonstrates POST with JSON body"""
    data = await request.json()
    return {
        "created": True,
        "user": data
    }


@app.get("/query")
async def query_params(request: FastRequest):
    """Query parameters demo"""
    name = request.get_query("name", "World")
    count = request.get_query("count", "1")
    return {
        "greeting": f"Hello, {name}!",
        "count": int(count)
    }


@app.get("/headers")
async def headers_demo(request: FastRequest):
    """Headers demo"""
    user_agent = request.get_header("user-agent", "Unknown")
    return {
        "user_agent": user_agent,
        "all_headers": dict(request.headers)
    }


@app.get("/error")
async def error_demo(request: FastRequest):
    """Error handling demo"""
    return FastJSONResponse(
        {"error": "Something went wrong", "code": "ERR_DEMO"},
        status=400
    )


if __name__ == "__main__":
    print("\n🚀 HasAPI Fast Demo")
    print("=" * 50)
    print("Endpoints:")
    print("  GET  /           - Welcome message")
    print("  GET  /json       - Complex JSON response")
    print("  GET  /users/{id} - Get user by ID")
    print("  POST /users      - Create user")
    print("  GET  /query      - Query parameters")
    print("  GET  /headers    - Headers info")
    print("  GET  /docs       - Swagger UI")
    print("=" * 50)
    
    # Run with auto-detected engine
    app.run(host="127.0.0.1", port=8000)
