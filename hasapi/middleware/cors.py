"""
HasAPI CORS Middleware

Handles Cross-Origin Resource Sharing (CORS) for API endpoints.
"""

from typing import List, Dict, Set, Optional, Union, Callable
from .base import BaseHTTPMiddleware
from ..response import Response
from ..utils import get_logger

logger = get_logger(__name__)


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware implementation.
    
    Handles preflight requests and adds appropriate CORS headers
    to enable cross-origin requests.
    """
    
    def __init__(
        self,
        allow_origins: Union[List[str], str, Callable] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600
    ):
        """
        Initialize CORS middleware.
        
        Args:
            allow_origins: List of allowed origins, "*" for all, or callable
            allow_methods: List of allowed HTTP methods
            allow_headers: List of allowed headers
            allow_credentials: Whether to allow credentials
            expose_headers: List of headers to expose to clients
            max_age: Max age for preflight cache in seconds
        """
        super().__init__()
        
        # Process allowed origins
        if allow_origins is None:
            self.allow_origins = []
        elif isinstance(allow_origins, str):
            self.allow_origins = [allow_origins]
        elif callable(allow_origins):
            self.allow_origins = allow_origins
        else:
            self.allow_origins = allow_origins
        
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or [
            "accept", "accept-language", "content-language", "content-type"
        ]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        
        # Pre-computed headers for performance
        self._simple_headers = {}
        self._preflight_headers = {}
        
        self._compute_headers()
    
    def _compute_headers(self):
        """Pre-compute headers for better performance"""
        # Simple headers (for non-preflight requests)
        if isinstance(self.allow_origins, list) and "*" in self.allow_origins:
            self._simple_headers["Access-Control-Allow-Origin"] = "*"
        elif self.allow_credentials:
            self._simple_headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.expose_headers:
            self._simple_headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        # Preflight headers
        self._preflight_headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        self._preflight_headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        self._preflight_headers["Access-Control-Max-Age"] = str(self.max_age)
        
        if isinstance(self.allow_origins, list) and "*" in self.allow_origins:
            self._preflight_headers["Access-Control-Allow-Origin"] = "*"
        elif self.allow_credentials:
            self._preflight_headers["Access-Control-Allow-Credentials"] = "true"
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if an origin is allowed"""
        if not origin:
            return False
        
        if isinstance(self.allow_origins, list):
            return "*" in self.allow_origins or origin in self.allow_origins
        elif callable(self.allow_origins):
            try:
                return self.allow_origins(origin)
            except Exception as e:
                logger.error(f"Error in origin callable: {e}")
                return False
        
        return False
    
    def _get_allow_origin_header(self, origin: str) -> Optional[str]:
        """Get the Access-Control-Allow-Origin header value"""
        if isinstance(self.allow_origins, list):
            if "*" in self.allow_origins:
                return "*"
            elif origin in self.allow_origins:
                return origin
        elif callable(self.allow_origins):
            try:
                if self.allow_origins(origin):
                    return origin
            except Exception as e:
                logger.error(f"Error in origin callable: {e}")
        
        return None
    
    async def before_request(self, request):
        """Process CORS headers before the request is handled"""
        origin = request.get_header("origin")
        
        # No origin header - not a cross-origin request
        if not origin:
            return None
        
        # Check if this is a preflight request
        if request.method == "OPTIONS":
            return await self._handle_preflight(request, origin)
        
        # Simple request - just add CORS headers
        return None
    
    async def after_request(self, request, response):
        """Add CORS headers to the response"""
        origin = request.get_header("origin")
        
        if not origin:
            return response
        
        # Add Access-Control-Allow-Origin if origin is allowed
        allow_origin = self._get_allow_origin_header(origin)
        if allow_origin:
            if not hasattr(response, "headers"):
                response.headers = {}
            response.headers["Access-Control-Allow-Origin"] = allow_origin
            
            # Add Vary header for proper caching
            if allow_origin != "*":
                existing_vary = response.headers.get("vary", "")
                if existing_vary:
                    if "origin" not in existing_vary.lower():
                        response.headers["vary"] = f"{existing_vary}, Origin"
                else:
                    response.headers["vary"] = "Origin"
        
        # Add other simple headers
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        return response
    
    async def _handle_preflight(self, request, origin: str):
        """Handle CORS preflight requests"""
        # Check if origin is allowed
        if not self._is_allowed_origin(origin):
            return Response(status_code=403, content=b"CORS: Origin not allowed")
        
        # Check if method is allowed
        requested_method = request.get_header("access-control-request-method")
        if requested_method and requested_method not in self.allow_methods:
            return Response(status_code=405, content=b"CORS: Method not allowed")
        
        # Check if headers are allowed
        requested_headers = request.get_header("access-control-request-headers")
        if requested_headers:
            requested_headers_list = [h.strip().lower() for h in requested_headers.split(",")]
            for header in requested_headers_list:
                if header not in [h.lower() for h in self.allow_headers]:
                    return Response(status_code=400, content=b"CORS: Header not allowed")
        
        # Create preflight response
        headers = {}
        
        # Add Access-Control-Allow-Origin
        allow_origin = self._get_allow_origin_header(origin)
        if allow_origin:
            headers["Access-Control-Allow-Origin"] = allow_origin
        
        # Add other preflight headers
        headers.update(self._preflight_headers)
        
        # Add Vary header for proper caching
        if allow_origin and allow_origin != "*":
            headers["vary"] = "Origin"
        
        return Response(
            status_code=204,  # No Content
            content=b"",
            headers=headers
        )


def add_cors_middleware(
    app,
    allow_origins: Union[List[str], str] = None,
    allow_methods: List[str] = None,
    allow_headers: List[str] = None,
    allow_credentials: bool = False,
    expose_headers: List[str] = None,
    max_age: int = 600
):
    """
    Convenience function to add CORS middleware to an app.
    
    Example:
        app = HasAPI()
        add_cors_middleware(app, allow_origins=["*"])
    """
    cors_middleware = CORSMiddleware(
        allow_origins=allow_origins,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        allow_credentials=allow_credentials,
        expose_headers=expose_headers,
        max_age=max_age
    )
    
    app.middleware(cors_middleware)
    return app