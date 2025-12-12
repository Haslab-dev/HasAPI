"""Tests for HasAPI application"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from hasapi import HasAPI, JSONResponse
from hasapi.request import Request
from hasapi.exceptions import HTTPException


class TestHasAPI:
    """Test HasAPI application functionality"""
    
    def setup_method(self):
        """Setup test app"""
        self.app = HasAPI(title="Test API", version="1.0.0", debug=True)
    
    async def test_root_route(self):
        """Test basic root route"""
        @self.app.get("/")
        async def root():
            return JSONResponse({"message": "Hello World"})
        
        # Create mock scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Mock send
        send = AsyncMock()
        
        # Call app
        await self.app(scope, receive, send)
        
        # Check response
        assert send.call_count == 2  # response.start + response.body
        
        # Check response start
        start_call = send.call_args_list[0][0]
        assert start_call["type"] == "http.response.start"
        assert start_call["status"] == 200
        
        # Check response body
        body_call = send.call_args_list[1][0]
        assert body_call["type"] == "http.response.body"
        assert b'"message": "Hello World"' in body_call["body"]
    
    async def test_path_params(self):
        """Test route with path parameters"""
        @self.app.get("/users/{user_id}")
        async def get_user(user_id: str):
            return JSONResponse({"user_id": user_id})
        
        # Create mock scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/users/123",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Mock send
        send = AsyncMock()
        
        # Call app
        await self.app(scope, receive, send)
        
        # Check response contains user_id
        body_call = send.call_args_list[1][0]
        assert b'"user_id": "123"' in body_call["body"]
    
    async def test_not_found(self):
        """Test 404 response"""
        # Create mock scope for non-existent route
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/nonexistent",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Mock send
        send = AsyncMock()
        
        # Call app
        await self.app(scope, receive, send)
        
        # Check 404 response
        start_call = send.call_args_list[0][0]
        assert start_call["status"] == 404
    
    async def test_exception_handling(self):
        """Test exception handling"""
        @self.app.get("/error")
        async def error_route():
            raise HTTPException(status_code=500, detail="Test error")
        
        # Create mock scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/error",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Mock send
        send = AsyncMock()
        
        # Call app
        await self.app(scope, receive, send)
        
        # Check error response
        start_call = send.call_args_list[0][0]
        assert start_call["status"] == 500
        
        body_call = send.call_args_list[1][0]
        assert b'"detail": "Test error"' in body_call["body"]
    
    def test_route_methods(self):
        """Test different HTTP methods"""
        methods = ["get", "post", "put", "delete", "patch", "options", "head"]
        
        for method in methods:
            # Add route
            route_decorator = getattr(self.app, method)
            route_decorator(f"/{method}")
            
            # Check route was added
            routes = self.app.router.get_routes_by_method(method.upper())
            assert len(routes) > 0
    
    async def test_startup_shutdown(self):
        """Test startup and shutdown handlers"""
        startup_called = False
        shutdown_called = False
        
        @self.app.on_event("startup")
        async def startup():
            nonlocal startup_called
            startup_called = True
        
        @self.app.on_event("shutdown")
        async def shutdown():
            nonlocal shutdown_called
            shutdown_called = True
        
        # Test startup
        await self.app.startup()
        assert startup_called
        
        # Test shutdown
        await self.app.shutdown()
        assert shutdown_called


class TestRequest:
    """Test Request class functionality"""
    
    def test_json_parsing(self):
        """Test JSON body parsing"""
        # Create mock scope with JSON content
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive with JSON body
        json_body = b'{"key": "value"}'
        receive = AsyncMock(side_effect=[
            {"type": "http.request.body", "body": json_body, "more_body": False}
        ])
        
        # Create request
        request = Request(scope, receive)
        
        # Test JSON parsing
        result = asyncio.run(request.json())
        assert result == {"key": "value"}
    
    def test_query_params(self):
        """Test query parameter parsing"""
        # Create mock scope with query string
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"param1=value1&param2=value2",
            "headers": [],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Create request
        request = Request(scope, receive)
        
        # Test query params
        assert request.query_params["param1"] == "value1"
        assert request.query_params["param2"] == "value2"
        assert request.get_query_param("param1") == "value1"
        assert request.get_query_param("nonexistent") is None
    
    def test_headers(self):
        """Test header parsing"""
        # Create mock scope with headers
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"x-custom-header", b"custom-value"),
                (b"authorization", b"Bearer token123")
            ],
            "client": ("127.0.0.1", 8000)
        }
        
        # Mock receive
        receive = AsyncMock(return_value={"type": "http.request.body", "body": b""})
        
        # Create request
        request = Request(scope, receive)
        
        # Test headers
        assert request.headers["x-custom-header"] == "custom-value"
        assert request.headers["authorization"] == "Bearer token123"
        assert request.get_header("x-custom-header") == "custom-value"
        assert request.get_header("nonexistent") is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])
