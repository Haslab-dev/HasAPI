"""
Minimal HasAPI Example

A simple example showing the basic HasAPI functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hasapi import HasAPI, JSONResponse
from hasapi.middleware import CORSMiddleware

# Create the app
app = HasAPI(title="Minimal API", version="1.0.0", debug=True)

# Add CORS middleware
app.middleware(CORSMiddleware(allow_origins=["*"]))

# Basic routes
@app.get("/")
async def root(request):
    """Root endpoint"""
    return JSONResponse({"message": "Hello from HasAPI!"})

@app.get("/health")
async def health(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "framework": "HasAPI"})

@app.get("/users/{user_id}")
async def get_user(request, user_id: str):
    """Get user by ID"""
    # Mock user data
    users = {
        "123": {"id": "123", "name": "Alice", "email": "alice@example.com"},
        "456": {"id": "456", "name": "Bob", "email": "bob@example.com"},
        "789": {"id": "789", "name": "Charlie", "email": "charlie@example.com"}
    }
    
    user = users.get(user_id)
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    
    return JSONResponse(user)

@app.post("/echo")
async def echo(request):
    """Echo back the request body"""
    body = await request.json()
    return JSONResponse({"echo": body, "timestamp": "2024-01-01T00:00:00Z"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
