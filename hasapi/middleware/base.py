"""
HasAPI Base Middleware Classes

Provides the foundation for building middleware components.
"""

from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, List, Optional
from functools import wraps

from ..utils import get_logger

logger = get_logger(__name__)


class Middleware(ABC):
    """
    Abstract base class for middleware.
    
    All middleware should inherit from this class and implement the
    process_request method.
    """
    
    def __init__(self, app=None):
        self.app = app
    
    @abstractmethod
    async def process_request(self, request, call_next, **kwargs):
        """
        Process the request and return a response.
        
        Args:
            request: The request object
            call_next: The next middleware in the chain
            **kwargs: Additional parameters (like path_params)
            
        Returns:
            Response object
        """
        pass
    
    async def __call__(self, request, call_next, **kwargs):
        """Make middleware callable"""
        return await self.process_request(request, call_next, **kwargs)


class MiddlewareStack:
    """
    Manages the execution order of middleware.
    
    Middleware are executed in the order they are added.
    """
    
    def __init__(self):
        self.middleware: List[Middleware] = []
        self._compiled_chain = None
        self._chain_dirty = True
    
    def add(self, middleware_class_or_instance):
        """
        Add middleware to the stack.
        
        Can accept either a middleware class or an instance.
        """
        if isinstance(middleware_class_or_instance, type):
            # It's a class, instantiate it
            middleware = middleware_class_or_instance()
        else:
            # It's already an instance
            middleware = middleware_class_or_instance
        
        self.middleware.append(middleware)
        self._chain_dirty = True  # Mark chain as needing recompilation
        return middleware
    
    def remove(self, middleware_class_or_instance):
        """Remove middleware from the stack"""
        if isinstance(middleware_class_or_instance, type):
            # Remove by class type
            self.middleware = [
                m for m in self.middleware 
                if not isinstance(m, middleware_class_or_instance)
            ]
        else:
            # Remove by instance
            if middleware_class_or_instance in self.middleware:
                self.middleware.remove(middleware_class_or_instance)
        self._chain_dirty = True  # Mark chain as needing recompilation
    
    async def process_request(self, request, handler, path_params=None):
        """
        Process a request through the middleware stack.
        
        Args:
            request: The request object
            handler: The final route handler
            path_params: Path parameters from route matching
            
        Returns:
            Response object
        """
        if path_params is None:
            path_params = {}
        
        # Fast path: no middleware
        if not self.middleware:
            if path_params:
                return await handler(request, **path_params)
            else:
                return await handler(request)
        
        # Build middleware chain (optimized with caching)
        async def execute_chain(idx=0):
            if idx >= len(self.middleware):
                # Reached the end, call the handler
                if path_params:
                    return await handler(request, **path_params)
                else:
                    return await handler(request)
            
            # Call current middleware
            middleware = self.middleware[idx]
            
            async def call_next(req):
                return await execute_chain(idx + 1)
            
            return await middleware.process_request(request, call_next)
        
        return await execute_chain()
    
    def _create_call_chain(self, handler, path_params):
        """
        Create the middleware call chain.
        
        Returns a callable that represents the entire middleware chain.
        """
        # Start with the final handler
        call_next = self._create_handler_call(handler, path_params)
        
        # Wrap with middleware in reverse order (last added runs first)
        for middleware in reversed(self.middleware):
            call_next = self._create_middleware_call(middleware, call_next)
        
        return call_next
    
    def _create_handler_call(self, handler, path_params):
        """Create a callable for the final route handler"""
        async def call_handler(request):
            # Call the route handler with path parameters
            if path_params:
                return await handler(request, **path_params)
            else:
                return await handler(request)
        
        return call_handler
    
    def _create_middleware_call(self, middleware, call_next):
        """Create a callable for a middleware"""
        async def call_middleware(request):
            return await middleware.process_request(request, call_next)
        
        return call_middleware


class BaseHTTPMiddleware(Middleware):
    """
    Base class for HTTP middleware with convenience methods.
    """
    
    async def process_request(self, request, call_next, **kwargs):
        """
        Process the request with before/after hooks.
        
        Subclasses can override before_request and after_request
        instead of implementing process_request directly.
        """
        # Process before request
        response = await self.before_request(request)
        if response is not None:
            return response
        
        # Call next middleware/handler
        response = await call_next(request, **kwargs)
        
        # Process after request
        response = await self.after_request(request, response)
        
        return response
    
    async def before_request(self, request):
        """
        Called before the request is processed.
        
        Return a response to short-circuit the request processing.
        Return None to continue processing.
        """
        pass
    
    async def after_request(self, request, response):
        """
        Called after the request is processed.
        
        Can modify the response before it's sent to the client.
        """
        return response


def middleware(middleware_class):
    """
    Decorator to convert a function into middleware.
    
    Example:
        @middleware
        async def timing_middleware(request, call_next):
            start = time.time()
            response = await call_next(request)
            duration = time.time() - start
            response.headers["X-Process-Time"] = str(duration)
            return response
    """
    class FunctionMiddleware(Middleware):
        async def process_request(self, request, call_next, **kwargs):
            return await middleware_class(request, call_next, **kwargs)
    
    return FunctionMiddleware


def create_middleware_decorator(middleware_class):
    """
    Create a decorator that adds middleware to an app.
    
    Example:
        @create_middleware_decorator(CORSMiddleware)
        def add_cors(app, **kwargs):
            app.middleware(CORSMiddleware(**kwargs))
    """
    def decorator(app=None, **kwargs):
        if app is None:
            # Return a decorator that will be applied to an app later
            def actual_decorator(app):
                app.middleware(middleware_class(**kwargs))
                return app
            return actual_decorator
        else:
            # Apply middleware directly
            app.middleware(middleware_class(**kwargs))
            return app
    
    return decorator