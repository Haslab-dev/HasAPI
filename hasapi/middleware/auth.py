"""
HasAPI Authentication Middleware

Provides authentication and authorization support for API endpoints.
"""

import jwt
import hashlib
import secrets
from typing import Dict, Any, Optional, Callable, Union, List
from datetime import datetime, timedelta
from .base import BaseHTTPMiddleware
from ..response import JSONResponse
from ..exceptions import HTTPException
from ..utils import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Base authentication middleware.
    
    Provides a framework for implementing various authentication schemes.
    """
    
    def __init__(
        self,
        auth_required: bool = True,
        exclude_paths: List[str] = None,
        get_user: Callable = None
    ):
        """
        Initialize authentication middleware.
        
        Args:
            auth_required: Whether authentication is required by default
            exclude_paths: List of paths that don't require authentication
            get_user: Function to get user from authentication token
        """
        super().__init__()
        self.auth_required = auth_required
        self.exclude_paths = exclude_paths or []
        self.get_user = get_user or self._default_get_user
    
    def _default_get_user(self, auth_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Default user extraction function"""
        return {"id": "anonymous", "username": "anonymous"}
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if a path is excluded from authentication"""
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    async def before_request(self, request):
        """Check authentication before processing the request"""
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.path):
            return None
        
        # Get authentication info from request
        auth_info = await self._extract_auth_info(request)
        
        if not auth_info and self.auth_required:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        # Get user from auth info
        user = None
        if auth_info:
            user = await self._get_user_async(auth_info)
        
        # Add user to request state
        if not hasattr(request, "state"):
            request.state = {}
        request.state.user = user
        request.state.auth_info = auth_info
        
        return None
    
    async def _extract_auth_info(self, request) -> Optional[Dict[str, Any]]:
        """Extract authentication information from the request"""
        # Override in subclasses
        return None
    
    async def _get_user_async(self, auth_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user from authentication info"""
        try:
            if callable(self.get_user):
                result = self.get_user(auth_info)
                if isinstance(result, dict):
                    return result
                elif hasattr(result, "__await__"):
                    return await result
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None


class JWTAuthMiddleware(AuthMiddleware):
    """
    JWT authentication middleware.
    
    Validates JWT tokens from the Authorization header.
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        auth_required: bool = True,
        exclude_paths: List[str] = None,
        get_user: Callable = None,
        token_header: str = "Authorization",
        token_prefix: str = "Bearer"
    ):
        """
        Initialize JWT authentication middleware.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm
            auth_required: Whether authentication is required by default
            exclude_paths: List of paths that don't require authentication
            get_user: Function to get user from JWT payload
            token_header: Header containing the token
            token_prefix: Token prefix (e.g., "Bearer")
        """
        super().__init__(auth_required, exclude_paths, get_user)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_header = token_header.lower()
        self.token_prefix = token_prefix
    
    async def _extract_auth_info(self, request) -> Optional[Dict[str, Any]]:
        """Extract JWT token from the Authorization header"""
        auth_header = request.get_header(self.token_header)
        
        if not auth_header:
            return None
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.token_prefix:
            return None
        
        token = parts[1]
        
        try:
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            return {"token": token, "payload": payload}
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
    
    def create_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """
        Create a JWT token.
        
        Args:
            payload: Token payload
            expires_in: Expiration time in seconds
            
        Returns:
            JWT token string
        """
        # Add expiration time
        payload = payload.copy()
        payload["exp"] = datetime.utcnow() + timedelta(seconds=expires_in)
        payload["iat"] = datetime.utcnow()
        
        # Create token
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )


class APIKeyAuthMiddleware(AuthMiddleware):
    """
    API Key authentication middleware.
    
    Validates API keys from headers or query parameters.
    """
    
    def __init__(
        self,
        api_keys: Union[List[str], Dict[str, Dict[str, Any]]],
        auth_required: bool = True,
        exclude_paths: List[str] = None,
        get_user: Callable = None,
        header_name: str = "X-API-Key",
        query_param: str = "api_key"
    ):
        """
        Initialize API Key authentication middleware.
        
        Args:
            api_keys: List of API keys or dict mapping keys to user info
            auth_required: Whether authentication is required by default
            exclude_paths: List of paths that don't require authentication
            get_user: Function to get user from API key
            header_name: Header name for API key
            query_param: Query parameter name for API key
        """
        super().__init__(auth_required, exclude_paths, get_user)
        
        if isinstance(api_keys, list):
            # Convert list to dict with empty user info
            self.api_keys = {key: {} for key in api_keys}
        else:
            self.api_keys = api_keys
        
        self.header_name = header_name.lower()
        self.query_param = query_param
    
    async def _extract_auth_info(self, request) -> Optional[Dict[str, Any]]:
        """Extract API key from headers or query parameters"""
        # Try header first
        api_key = request.get_header(self.header_name)
        
        # Try query parameter if not in header
        if not api_key:
            api_key = request.get_query_param(self.query_param)
        
        if not api_key:
            return None
        
        # Validate API key
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        return {"api_key": api_key, "user_info": self.api_keys[api_key]}
    
    def generate_api_key(self, user_info: Dict[str, Any] = None) -> str:
        """
        Generate a new API key.
        
        Args:
            user_info: User information associated with the key
            
        Returns:
            Generated API key
        """
        # Generate secure random key
        api_key = secrets.token_urlsafe(32)
        
        # Store with user info
        self.api_keys[api_key] = user_info or {}
        
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if key was revoked, False if key didn't exist
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            return True
        return False


class SessionAuthMiddleware(AuthMiddleware):
    """
    Session-based authentication middleware.
    
    Validates session cookies for authentication.
    """
    
    def __init__(
        self,
        session_store: Dict[str, Dict[str, Any]],
        auth_required: bool = True,
        exclude_paths: List[str] = None,
        get_user: Callable = None,
        cookie_name: str = "session_id",
        max_age: int = 86400  # 24 hours
    ):
        """
        Initialize session authentication middleware.
        
        Args:
            session_store: Dictionary to store session data
            auth_required: Whether authentication is required by default
            exclude_paths: List of paths that don't require authentication
            get_user: Function to get user from session
            cookie_name: Name of the session cookie
            max_age: Maximum age of session in seconds
        """
        super().__init__(auth_required, exclude_paths, get_user)
        self.session_store = session_store
        self.cookie_name = cookie_name
        self.max_age = max_age
    
    async def _extract_auth_info(self, request) -> Optional[Dict[str, Any]]:
        """Extract session ID from cookies"""
        # Parse cookies from headers
        cookie_header = request.get_header("cookie")
        if not cookie_header:
            return None
        
        # Parse cookies
        cookies = {}
        for cookie in cookie_header.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookies[name.strip()] = value.strip()
        
        session_id = cookies.get(self.cookie_name)
        if not session_id:
            return None
        
        # Validate session
        session = self.session_store.get(session_id)
        if not session:
            return None
        
        # Check session expiration
        created_at = session.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            if datetime.utcnow() - created_at > timedelta(seconds=self.max_age):
                # Session expired
                del self.session_store[session_id]
                return None
        
        return {"session_id": session_id, "session": session}
    
    def create_session(self, user_info: Dict[str, Any]) -> str:
        """
        Create a new session.
        
        Args:
            user_info: User information to store in session
            
        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        
        self.session_store[session_id] = {
            "user_info": user_info,
            "created_at": datetime.utcnow()
        }
        
        return session_id
    
    def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session.
        
        Args:
            session_id: Session ID to destroy
            
        Returns:
            True if session was destroyed, False if it didn't exist
        """
        if session_id in self.session_store:
            del self.session_store[session_id]
            return True
        return False