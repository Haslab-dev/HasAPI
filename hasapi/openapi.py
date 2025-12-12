"""
OpenAPI decorators and utilities for HasAPI
"""

from typing import Dict, Any, Optional, List
from functools import wraps


def api_doc(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List]]] = None
):
    """
    Decorator to add OpenAPI documentation to route handlers.
    
    Example:
        @app.post("/api/items")
        @api_doc(
            summary="Create item",
            tags=["Items"],
            request_body={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"}
                },
                "required": ["name"]
            },
            security=[{"bearerAuth": []}]
        )
        async def create_item(request):
            pass
    """
    def decorator(func):
        # Store OpenAPI metadata on the function
        if not hasattr(func, '_openapi'):
            func._openapi = {}
        
        if summary:
            func._openapi['summary'] = summary
        if description:
            func._openapi['description'] = description
        if tags:
            func._openapi['tags'] = tags
        if request_body:
            func._openapi['request_body'] = request_body
        if responses:
            func._openapi['responses'] = responses
        if security is not None:
            func._openapi['security'] = security
        
        return func
    
    return decorator


def request_body(schema: Dict[str, Any], description: str = "Request body"):
    """
    Decorator to define request body schema.
    
    Example:
        @app.post("/api/items")
        @request_body({
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"}
            }
        })
        async def create_item(request):
            pass
    """
    return api_doc(request_body={"description": description, "schema": schema})


def response(status_code: int, schema: Dict[str, Any], description: str = "Response"):
    """
    Decorator to define response schema.
    
    Example:
        @app.get("/api/items")
        @response(200, {
            "type": "object",
            "properties": {
                "items": {"type": "array"}
            }
        })
        async def list_items(request):
            pass
    """
    return api_doc(responses={
        str(status_code): {
            "description": description,
            "schema": schema
        }
    })


def requires_auth():
    """
    Decorator to mark endpoint as requiring authentication.
    
    Example:
        @app.post("/api/items")
        @requires_auth()
        async def create_item(request):
            pass
    """
    return api_doc(security=[{"bearerAuth": []}])
