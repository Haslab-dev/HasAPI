"""
HasAPI Cached Router - Zero-overhead route matching

Hot path requirements:
- Dict lookup for static routes
- Tuple lookup for dynamic routes  
- No regex at runtime
- Pre-compiled route patterns
"""

from __future__ import annotations
import re
from typing import Dict, List, Callable, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .request import FastRequest


@dataclass(slots=True, frozen=True)
class CompiledRoute:
    """Immutable compiled route - created at startup, never modified at runtime"""
    path: str
    handler: Callable
    methods: frozenset
    param_names: tuple
    # For dynamic routes only
    pattern: Optional[re.Pattern] = None
    
    def match_params(self, path: str) -> Optional[Dict[str, str]]:
        """Extract params from path - only called for dynamic routes"""
        if self.pattern is None:
            return {} if path == self.path else None
        
        match = self.pattern.match(path)
        if not match:
            return None
        
        return dict(zip(self.param_names, match.groups()))


class CachedRouter:
    """
    High-performance router with O(1) lookups for static routes.
    
    Architecture:
    - Static routes: Direct dict lookup by (method, path)
    - Dynamic routes: Ordered list with pre-compiled patterns
    
    All compilation happens at startup. Runtime is pure lookups.
    """
    
    __slots__ = ('_static_routes', '_dynamic_routes', '_compiled', '_all_routes')
    
    def __init__(self):
        # Static routes: {(method, path): CompiledRoute}
        self._static_routes: Dict[Tuple[str, str], CompiledRoute] = {}
        # Dynamic routes: [(CompiledRoute, ...)] per method
        self._dynamic_routes: Dict[str, List[CompiledRoute]] = {}
        # Track if compiled
        self._compiled = False
        # All routes for introspection
        self._all_routes: List[CompiledRoute] = []
    
    def add_route(
        self, 
        path: str, 
        handler: Callable, 
        methods: List[str]
    ) -> CompiledRoute:
        """
        Add route at startup time.
        
        This is allowed to be slow - it only runs once.
        """
        if self._compiled:
            raise RuntimeError("Cannot add routes after compilation")
        
        methods_frozen = frozenset(m.upper() for m in methods)
        is_dynamic = '{' in path
        
        if is_dynamic:
            pattern, param_names = self._compile_pattern(path)
            route = CompiledRoute(
                path=path,
                handler=handler,
                methods=methods_frozen,
                param_names=tuple(param_names),
                pattern=pattern
            )
        else:
            route = CompiledRoute(
                path=path,
                handler=handler,
                methods=methods_frozen,
                param_names=(),
                pattern=None
            )
        
        self._all_routes.append(route)
        return route
    
    def compile(self) -> None:
        """
        Compile all routes into optimized lookup structures.
        
        Called once at startup. After this, no modifications allowed.
        """
        if self._compiled:
            return
        
        for route in self._all_routes:
            if route.pattern is None:
                # Static route - add to dict for each method
                for method in route.methods:
                    key = (method, route.path)
                    self._static_routes[key] = route
            else:
                # Dynamic route - add to list for each method
                for method in route.methods:
                    if method not in self._dynamic_routes:
                        self._dynamic_routes[method] = []
                    self._dynamic_routes[method].append(route)
        
        self._compiled = True
    
    def match(
        self, 
        method: str, 
        path: str
    ) -> Tuple[Optional[CompiledRoute], Dict[str, str]]:
        """
        Match route - HOT PATH.
        
        This must be as fast as possible:
        1. Dict lookup for static routes
        2. Linear scan for dynamic routes (usually few)
        """
        method = method.upper()
        
        # Fast path: static route lookup
        key = (method, path)
        route = self._static_routes.get(key)
        if route is not None:
            return route, {}
        
        # Slow path: dynamic route matching
        dynamic_routes = self._dynamic_routes.get(method)
        if dynamic_routes:
            for route in dynamic_routes:
                params = route.match_params(path)
                if params is not None:
                    return route, params
        
        return None, {}
    
    def _compile_pattern(self, path: str) -> Tuple[re.Pattern, List[str]]:
        """Compile path pattern at startup"""
        param_names = []
        pattern_parts = []
        
        for part in path.split('/'):
            if not part:
                continue
            
            if part.startswith('{') and part.endswith('}'):
                param_name = part[1:-1]
                # Support type hints: {id:int}
                if ':' in param_name:
                    param_name, _ = param_name.split(':', 1)
                param_names.append(param_name)
                pattern_parts.append('([^/]+)')
            else:
                pattern_parts.append(re.escape(part))
        
        pattern_str = '^/' + '/'.join(pattern_parts) + '$'
        return re.compile(pattern_str), param_names
    
    def get_all_routes(self) -> List[CompiledRoute]:
        """Get all routes for introspection (docs, etc)"""
        return self._all_routes.copy()
