"""
HasAPI Full REST API Example

Complete REST API with:
- CORS middleware
- JWT Authentication
- Swagger/OpenAPI documentation
- CRUD operations
- Error handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from hasapi import HasAPI, JSONResponse, api_doc, requires_auth
from hasapi.middleware import CORSMiddleware, JWTAuthMiddleware

from dotenv import load_dotenv
load_dotenv()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# In-memory storage
users_db: Dict[str, Dict] = {
    "admin": {"id": "1", "username": "admin", "email": "admin@example.com", "password": "admin123", "role": "admin"},
    "user": {"id": "2", "username": "user", "email": "user@example.com", "password": "user123", "role": "user"}
}
items_db: Dict[str, Dict] = {}
item_counter = 0

app = HasAPI(title="Full REST API", version="1.0.0", debug=True)
app.middleware(CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]))


def create_token(user_id: str, username: str, role: str) -> str:
    """Create JWT token"""
    import jwt
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    """Verify JWT token"""
    import jwt
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None


def get_current_user(request) -> Optional[Dict]:
    """Get current user from request"""
    auth_header = None
    for header_name, header_value in request.scope.get("headers", []):
        if header_name.decode().lower() == "authorization":
            auth_header = header_value.decode()
            break
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)


@app.get("/")
async def root(request):
    """Root endpoint with API information"""
    return JSONResponse({
        "message": "Welcome to Full REST API",
        "version": "1.0.0",
        "docs": "/docs"
    })


@app.get("/api/health")
async def health(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_users": len(users_db),
        "total_items": len(items_db)
    })


@app.post("/api/auth/login")
async def login(request):
    """Login endpoint"""
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    
    if not username or not password:
        return JSONResponse({"error": "Username and password required"}, status_code=400)
    
    user = users_db.get(username)
    if not user or user["password"] != password:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    
    token = create_token(user["id"], user["username"], user["role"])
    return JSONResponse({
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]}
    })


@app.post("/api/auth/register")
async def register(request):
    """Register new user"""
    body = await request.json()
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")
    
    if not username or not email or not password:
        return JSONResponse({"error": "Username, email, and password required"}, status_code=400)
    
    if username in users_db:
        return JSONResponse({"error": "Username already exists"}, status_code=400)
    
    user_id = str(len(users_db) + 1)
    users_db[username] = {"id": user_id, "username": username, "email": email, "password": password, "role": "user"}
    token = create_token(user_id, username, "user")
    
    return JSONResponse({
        "access_token": token,
        "user": {"id": user_id, "username": username, "role": "user"}
    }, status_code=201)


@app.get("/api/auth/me")
async def get_me(request):
    """Get current user info"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return JSONResponse({"user": user})


@app.get("/api/items")
async def list_items(request):
    """List all items"""
    return JSONResponse({"items": list(items_db.values()), "total": len(items_db)})


@app.get("/api/items/{item_id}")
async def get_item(request, item_id: str):
    """Get single item by ID"""
    item = items_db.get(item_id)
    if not item:
        return JSONResponse({"error": "Item not found"}, status_code=404)
    return JSONResponse(item)


@app.post("/api/items")
async def create_item(request):
    """Create new item"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    body = await request.json()
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "Name is required"}, status_code=400)
    
    global item_counter
    item_counter += 1
    item_id = str(item_counter)
    
    item = {
        "id": item_id,
        "name": name,
        "description": body.get("description", ""),
        "price": body.get("price", 0),
        "created_by": user["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    items_db[item_id] = item
    return JSONResponse(item, status_code=201)


@app.put("/api/items/{item_id}")
async def update_item(request, item_id: str):
    """Update item"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    item = items_db.get(item_id)
    if not item:
        return JSONResponse({"error": "Item not found"}, status_code=404)
    
    body = await request.json()
    if "name" in body:
        item["name"] = body["name"]
    if "description" in body:
        item["description"] = body["description"]
    if "price" in body:
        item["price"] = body["price"]
    
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    return JSONResponse(item)


@app.delete("/api/items/{item_id}")
async def delete_item(request, item_id: str):
    """Delete item"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    if item_id not in items_db:
        return JSONResponse({"error": "Item not found"}, status_code=404)
    
    del items_db[item_id]
    return JSONResponse({"message": "Item deleted successfully"})


if __name__ == "__main__":
    import uvicorn
    print("Starting HasAPI Full REST API on http://localhost:8000")
    print("Swagger Docs: http://localhost:8000/docs")
    print("Test credentials: admin/admin123 or user/user123")
    uvicorn.run(app, host="0.0.0.0", port=8000)
