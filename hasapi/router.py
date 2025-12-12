"""
HasAPI Router Module

Handles route registration, matching, and parameter extraction.
"""

import re
from typing import Dict, List, Callable, Optional, Tuple, Any, Pattern
from dataclasses import dataclass

from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class Route:
    """Represents a single route in the application"""
    path: str
    handler: Callable
    methods: List[str]
    pattern: Pattern
    param_names: List[str]
    
    def __post_init__(self):
        """Ensure methods are uppercase"""
        self.methods = [method.upper() for method in self.methods]


@dataclass
class WebSocketRoute:
    """Represents a WebSocket route"""
    path: str
    handler: Callable
    pattern: Pattern
    param_names: List[str]


class Router:
    """
    Router class for handling HTTP and WebSocket routes.
    
    Provides fast route matching with parameter extraction.
    """
    
    def __init__(self):
        self.routes: Dict[str, List[Route]] = {}
        self.websocket_routes: List[WebSocketRoute] = []
        
        # HTTP methods to track
        self.http_methods = {
            "GET", "POST", "PUT", "DELETE", "PATCH", 
            "OPTIONS", "HEAD", "TRACE", "CONNECT"
        }
        
        # Cache for static routes (no path params)
        self._static_route_cache: Dict[str, Dict[str, Route]] = {}
    
    def add_route(self, path: str, handler: Callable, methods: List[str]):
        """Add a new route to the router"""
        # Validate methods
        for method in methods:
            if method.upper() not in self.http_methods:
                raise ValueError(f"Invalid HTTP method: {method}")
        
        # Convert path to regex pattern
        pattern, param_names = self._path_to_pattern(path)
        
        # Create route
        route = Route(
            path=path,
            handler=handler,
            methods=methods,
            pattern=pattern,
            param_names=param_names
        )
        
        # Add to routes dict for each method
        for method in methods:
            method_upper = method.upper()
            if method_upper not in self.routes:
                self.routes[method_upper] = []
            self.routes[method_upper].append(route)
        
        logger.debug(f"Added route: {methods} {path}")
    
    def add_websocket_route(self, path: str, handler: Callable):
        """Add a WebSocket route"""
        pattern, param_names = self._path_to_pattern(path)
        
        ws_route = WebSocketRoute(
            path=path,
            handler=handler,
            pattern=pattern,
            param_names=param_names
        )
        
        self.websocket_routes.append(ws_route)
        logger.debug(f"Added WebSocket route: {path}")
    
    def match_route(self, method: str, path: str) -> Tuple[Optional[Route], Dict[str, Any]]:
        """
        Match a route based on method and path.
        
        Returns:
            Tuple of (Route, path_params) or (None, {}) if no match
        """
        method_upper = method.upper()
        
        if method_upper not in self.routes:
            return None, {}
        
        # Fast path: check static route cache first
        cache_key = f"{method_upper}:{path}"
        if cache_key in self._static_route_cache:
            cached = self._static_route_cache[cache_key]
            return cached['route'], cached['params']
        
        # Try to match routes in order they were added
        for route in self.routes[method_upper]:
            match = route.pattern.match(path)
            if match:
                # Extract path parameters
                path_params = {}
                for i, param_name in enumerate(route.param_names):
                    path_params[param_name] = match.group(i + 1)
                
                # Cache static routes (no params) for faster lookup next time
                if not path_params:
                    self._static_route_cache[cache_key] = {
                        'route': route,
                        'params': path_params
                    }
                
                return route, path_params
        
        return None, {}
    
    def match_websocket_route(self, path: str) -> Optional[WebSocketRoute]:
        """Match a WebSocket route based on path"""
        for ws_route in self.websocket_routes:
            match = ws_route.pattern.match(path)
            if match:
                return ws_route
        
        return None
    
    def _path_to_pattern(self, path: str) -> Tuple[Pattern, List[str]]:
        """
        Convert a path string to a regex pattern and extract parameter names.
        
        Examples:
            "/users/{user_id}" -> ("/users/([^/]+)", ["user_id"])
            "/files/{category}/{filename}" -> ("/files/([^/]+)/([^/]+)", ["category", "filename"])
        """
        if not path.startswith("/"):
            raise ValueError("Path must start with '/'")
        
        # Escape special regex characters except for our parameter markers
        escaped_path = re.escape(path)
        escaped_path = escaped_path.replace(r'\{', '{').replace(r'\}', '}')
        
        # Replace {param} with regex capture group
        pattern_str = re.sub(r'\{([^}]+)\}', r'([^/]+)', escaped_path)
        
        # Ensure exact match
        pattern_str = f"^{pattern_str}$"
        
        # Extract parameter names
        param_names = re.findall(r'\{([^}]+)\}', path)
        
        return re.compile(pattern_str), param_names
    
    def get_all_routes(self) -> List[Route]:
        """Get all registered routes"""
        all_routes = []
        for method_routes in self.routes.values():
            all_routes.extend(method_routes)
        return all_routes
    
    def get_all_websocket_routes(self) -> List[WebSocketRoute]:
        """Get all registered WebSocket routes"""
        return self.websocket_routes.copy()
    
    def get_routes_by_method(self, method: str) -> List[Route]:
        """Get all routes for a specific HTTP method"""
        method_upper = method.upper()
        return self.routes.get(method_upper, []).copy()
    
    def generate_openapi_paths(self) -> Dict[str, Any]:
        """Generate OpenAPI paths specification for all routes"""
        import inspect
        
        paths = {}
        
        for route in self.get_all_routes():
            if route.path not in paths:
                paths[route.path] = {}
            
            for method in route.methods:
                method_lower = method.lower()
                
                # Check if handler has OpenAPI metadata
                openapi_meta = getattr(route.handler, '_openapi', {})
                
                # Extract docstring from handler
                docstring = inspect.getdoc(route.handler) or f"{method} {route.path}"
                summary = openapi_meta.get('summary') or (docstring.split('\n')[0] if docstring else f"{method} {route.path}")
                description = openapi_meta.get('description') or (docstring if len(docstring.split('\n')) > 1 else None)
                
                # Determine tag from path or metadata
                if 'tags' in openapi_meta:
                    tags = openapi_meta['tags']
                else:
                    path_parts = route.path.strip('/').split('/')
                    tag = path_parts[0] if path_parts and path_parts[0] else "default"
                    if tag.startswith('api'):
                        tag = path_parts[1] if len(path_parts) > 1 else "api"
                    tags = [tag.capitalize()]
                
                # Basic OpenAPI operation
                operation = {
                    "summary": summary,
                    "tags": tags
                }
                
                if description:
                    operation["description"] = description
                
                # Use custom responses or default
                if 'responses' in openapi_meta:
                    operation["responses"] = {}
                    for status, resp_data in openapi_meta['responses'].items():
                        operation["responses"][status] = {
                            "description": resp_data.get("description", "Response"),
                            "content": {
                                "application/json": {
                                    "schema": resp_data.get("schema", {"type": "object"})
                                }
                            }
                        }
                else:
                    operation["responses"] = {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                
                # Add path parameters
                if route.param_names:
                    parameters = []
                    for param_name in route.param_names:
                        parameters.append({
                            "name": param_name,
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": f"Path parameter: {param_name}"
                        })
                    operation["parameters"] = parameters
                
                # Add request body from metadata or default for POST, PUT, PATCH
                if 'request_body' in openapi_meta:
                    rb = openapi_meta['request_body']
                    operation["requestBody"] = {
                        "required": True,
                        "description": rb.get("description", "Request body"),
                        "content": {
                            "application/json": {
                                "schema": rb.get("schema", {"type": "object"})
                            }
                        }
                    }
                elif method_lower in ['post', 'put', 'patch']:
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                
                # Add security from metadata or heuristic
                if 'security' in openapi_meta:
                    operation["security"] = openapi_meta['security']
                elif 'auth' not in route.path and route.path not in ['/', '/api/health', '/docs', '/openapi.json']:
                    # Check if handler name or path suggests it needs auth
                    handler_name = route.handler.__name__ if hasattr(route.handler, '__name__') else ''
                    if any(keyword in route.path.lower() for keyword in ['admin', 'user', 'profile']) or \
                       any(keyword in handler_name.lower() for keyword in ['create', 'update', 'delete']):
                        operation["security"] = [{"bearerAuth": []}]
                
                paths[route.path][method_lower] = operation
        
        return paths