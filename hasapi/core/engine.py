"""
HasAPI Execution Engine - The heart of the hot path

This is where requests become responses. No HTTP concerns here.
Just: request in -> handler call -> response out

Design:
- Pre-bound handlers at startup
- Zero reflection at runtime
- Minimal async overhead
"""

from __future__ import annotations
import asyncio
import inspect
from typing import Dict, List, Callable, Any, Optional, Tuple, TYPE_CHECKING
from functools import partial

import orjson

from .router import CachedRouter, CompiledRoute
from .request import FastRequest
from .response import FastJSONResponse, fast_json_response

if TYPE_CHECKING:
    pass


class ExecutionEngine:
    """
    Request execution engine - processes requests through handlers.
    
    Startup phase:
    - Compile routes
    - Bind middleware
    - Wrap handlers
    
    Runtime phase (HOT PATH):
    - Route lookup (dict)
    - Handler call (direct)
    - Response serialization (orjson)
    """
    
    __slots__ = (
        'router', 'middleware', '_compiled',
        '_error_handler', '_not_found_handler'
    )
    
    def __init__(self):
        self.router = CachedRouter()
        self.middleware: List[Callable] = []
        self._compiled = False
        self._error_handler: Optional[Callable] = None
        self._not_found_handler: Optional[Callable] = None
    
    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: List[str]
    ) -> CompiledRoute:
        """Add route at startup"""
        if self._compiled:
            raise RuntimeError("Cannot add routes after compilation")
        return self.router.add_route(path, handler, methods)
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware at startup"""
        if self._compiled:
            raise RuntimeError("Cannot add middleware after compilation")
        self.middleware.append(middleware)
    
    def set_error_handler(self, handler: Callable) -> None:
        """Set custom error handler"""
        self._error_handler = handler
    
    def set_not_found_handler(self, handler: Callable) -> None:
        """Set custom 404 handler"""
        self._not_found_handler = handler
    
    def compile(self) -> None:
        """
        Compile engine for runtime.
        
        After this:
        - Routes are frozen
        - Middleware chain is built
        - Handlers are wrapped
        """
        if self._compiled:
            return
        
        self.router.compile()
        self._compiled = True
    
    async def execute(self, request: FastRequest) -> Any:
        """
        Execute request - HOT PATH.
        
        This is the core execution loop:
        1. Route lookup
        2. Middleware chain
        3. Handler call
        4. Response creation
        """
        # Route lookup
        route, params = self.router.match(request.method, request.path)
        
        if route is None:
            return await self._handle_not_found(request)
        
        # Attach path params to request
        request.path_params = params
        
        try:
            # Call handler directly
            result = await self._call_handler(route.handler, request)
            return self._normalize_response(result)
        except Exception as e:
            return await self._handle_error(request, e)
    
    async def _call_handler(self, handler: Callable, request: FastRequest) -> Any:
        """Call handler with request"""
        # Check if handler is async
        if asyncio.iscoroutinefunction(handler):
            return await handler(request)
        else:
            # Sync handler - run in thread pool for safety
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, handler, request)
    
    def _normalize_response(self, result: Any) -> Any:
        """
        Normalize handler result to response.
        
        Handlers can return:
        - dict/list -> JSONResponse
        - str -> TextResponse
        - bytes -> raw bytes
        - Response object -> pass through
        - tuple (data, status) -> JSONResponse with status
        - tuple (data, status, headers) -> JSONResponse with status and headers
        """
        if result is None:
            return FastJSONResponse({})
        
        if isinstance(result, (FastJSONResponse,)):
            return result
        
        # Check for ASGI response (has __call__)
        if hasattr(result, '__call__') and asyncio.iscoroutinefunction(result.__call__):
            return result
        
        if isinstance(result, tuple):
            if len(result) == 2:
                data, status = result
                return FastJSONResponse(data, status=status)
            elif len(result) == 3:
                data, status, headers = result
                return FastJSONResponse(data, status=status, headers=headers)
        
        if isinstance(result, (dict, list)):
            return FastJSONResponse(result)
        
        if isinstance(result, str):
            from .response import FastTextResponse
            return FastTextResponse(result)
        
        if isinstance(result, bytes):
            from .response import FastResponse
            return FastResponse(result)
        
        # Default: try to serialize as JSON
        return FastJSONResponse(result)
    
    async def _handle_not_found(self, request: FastRequest) -> Any:
        """Handle 404"""
        if self._not_found_handler:
            return await self._call_handler(self._not_found_handler, request)
        
        return FastJSONResponse(
            {'error': 'Not Found', 'path': request.path},
            status=404
        )
    
    async def _handle_error(self, request: FastRequest, error: Exception) -> Any:
        """Handle errors"""
        if self._error_handler:
            try:
                return await self._error_handler(request, error)
            except Exception:
                pass
        
        # Default error response
        return FastJSONResponse(
            {'error': 'Internal Server Error', 'detail': str(error)},
            status=500
        )
    
    def get_routes(self) -> List[CompiledRoute]:
        """Get all routes for introspection"""
        return self.router.get_all_routes()
