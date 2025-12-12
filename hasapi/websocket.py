"""
HasAPI WebSocket Module

Provides WebSocket support for real-time communication.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum

from .utils import get_logger

logger = get_logger(__name__)


class WebSocketState(Enum):
    """WebSocket connection states"""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    ERROR = 3


class WebSocketDisconnect(Exception):
    """Exception raised when WebSocket is disconnected"""
    
    def __init__(self, code: int = 1000, reason: str = ""):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected: {code} {reason}")


class WebSocket:
    """
    WebSocket connection handler.
    
    Provides methods for sending and receiving messages over WebSocket connections.
    """
    
    def __init__(self, scope: dict, receive: callable, send: callable):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.state = WebSocketState.CONNECTING
        self._accepted = False
        self._close_code = None
        self._close_reason = None
    
    @property
    def query_params(self) -> Dict[str, str]:
        """Get query parameters from the WebSocket URL"""
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        from urllib.parse import parse_qs
        
        if query_string:
            parsed = parse_qs(query_string, keep_blank_values=True)
            return {
                k: v[0] if len(v) == 1 else v 
                for k, v in parsed.items()
            }
        return {}
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get headers from the WebSocket connection"""
        headers = {}
        for name, value in self.scope.get("headers", []):
            headers[name.decode("utf-8")] = value.decode("utf-8")
        return headers
    
    @property
    def client(self) -> Optional[tuple]:
        """Get client address"""
        return self.scope.get("client")
    
    @property
    def path(self) -> str:
        """Get the WebSocket path"""
        return self.scope.get("path", "")
    
    async def accept(self, subprotocol: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """
        Accept the WebSocket connection.
        
        Args:
            subprotocol: Optional WebSocket subprotocol
            headers: Optional additional headers
        """
        if self._accepted:
            return
        
        message = {"type": "websocket.accept"}
        
        if subprotocol:
            message["subprotocol"] = subprotocol
        
        if headers:
            message["headers"] = [
                (name.encode("utf-8"), value.encode("utf-8"))
                for name, value in headers.items()
            ]
        
        await self.send(message)
        self._accepted = True
        self.state = WebSocketState.CONNECTED
        
        logger.debug(f"WebSocket connection accepted: {self.path}")
    
    async def receive_text(self) -> str:
        """Receive a text message"""
        if not self._accepted:
            await self.accept()
        
        message = await self.receive()
        
        if message["type"] == "websocket.receive":
            if "text" in message:
                return message["text"]
            elif "bytes" in message:
                return message["bytes"].decode("utf-8")
        elif message["type"] == "websocket.disconnect":
            self.state = WebSocketState.DISCONNECTED
            self._close_code = message.get("code", 1000)
            self._close_reason = message.get("reason", "")
            raise WebSocketDisconnect(self._close_code, self._close_reason)
        
        raise WebSocketDisconnect(1006, "Connection lost")
    
    async def receive_bytes(self) -> bytes:
        """Receive a binary message"""
        if not self._accepted:
            await self.accept()
        
        message = await self.receive()
        
        if message["type"] == "websocket.receive":
            if "bytes" in message:
                return message["bytes"]
            elif "text" in message:
                return message["text"].encode("utf-8")
        elif message["type"] == "websocket.disconnect":
            self.state = WebSocketState.DISCONNECTED
            self._close_code = message.get("code", 1000)
            self._close_reason = message.get("reason", "")
            raise WebSocketDisconnect(self._close_code, self._close_reason)
        
        raise WebSocketDisconnect(1006, "Connection lost")
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive a JSON message"""
        text = await self.receive_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    async def send_text(self, data: str):
        """Send a text message"""
        if not self._accepted:
            await self.accept()
        
        await self.send({
            "type": "websocket.send",
            "text": data
        })
    
    async def send_bytes(self, data: bytes):
        """Send a binary message"""
        if not self._accepted:
            await self.accept()
        
        await self.send({
            "type": "websocket.send",
            "bytes": data
        })
    
    async def send_json(self, data: Dict[str, Any]):
        """Send a JSON message"""
        text = json.dumps(data)
        await self.send_text(text)
    
    async def close(self, code: int = 1000, reason: str = ""):
        """
        Close the WebSocket connection.
        
        Args:
            code: WebSocket close code
            reason: Close reason
        """
        if self.state == WebSocketState.DISCONNECTED:
            return
        
        await self.send({
            "type": "websocket.close",
            "code": code,
            "reason": reason
        })
        
        self.state = WebSocketState.DISCONNECTED
        self._close_code = code
        self._close_reason = reason
        
        logger.debug(f"WebSocket connection closed: {code} {reason}")
    
    async def ping(self, data: bytes = b""):
        """Send a ping frame"""
        if not self._accepted:
            await self.accept()
        
        await self.send({
            "type": "websocket.ping",
            "data": data
        })
    
    async def pong(self, data: bytes = b""):
        """Send a pong frame"""
        if not self._accepted:
            await self.accept()
        
        await self.send({
            "type": "websocket.pong",
            "data": data
        })
    
    def __aiter__(self):
        """Make WebSocket iterable"""
        return self
    
    async def __anext__(self):
        """Async iterator for receiving messages"""
        try:
            return await self.receive_text()
        except WebSocketDisconnect:
            raise StopAsyncIteration
    
    def __repr__(self) -> str:
        return f"WebSocket(path={self.path}, state={self.state.name})"


class WebSocketManager:
    """
    Manager for multiple WebSocket connections.
    
    Provides functionality for broadcasting messages to multiple clients
    and managing connection groups.
    """
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.groups: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
    
    async def add_connection(self, connection_id: str, websocket: WebSocket):
        """Add a WebSocket connection"""
        async with self._lock:
            self.connections[connection_id] = websocket
            logger.debug(f"Added WebSocket connection: {connection_id}")
    
    async def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if connection_id in self.connections:
                del self.connections[connection_id]
                
                # Remove from all groups
                for group_id, connections in self.groups.items():
                    if connection_id in connections:
                        connections.remove(connection_id)
                
                logger.debug(f"Removed WebSocket connection: {connection_id}")
    
    async def add_to_group(self, connection_id: str, group_id: str):
        """Add a connection to a group"""
        async with self._lock:
            if group_id not in self.groups:
                self.groups[group_id] = []
            
            if connection_id not in self.groups[group_id]:
                self.groups[group_id].append(connection_id)
                logger.debug(f"Added {connection_id} to group {group_id}")
    
    async def remove_from_group(self, connection_id: str, group_id: str):
        """Remove a connection from a group"""
        async with self._lock:
            if group_id in self.groups and connection_id in self.groups[group_id]:
                self.groups[group_id].remove(connection_id)
                logger.debug(f"Removed {connection_id} from group {group_id}")
    
    async def send_to_connection(self, connection_id: str, message: Union[str, bytes, Dict[str, Any]]):
        """Send a message to a specific connection"""
        async with self._lock:
            if connection_id not in self.connections:
                return False
            
            websocket = self.connections[connection_id]
            
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                elif isinstance(message, bytes):
                    await websocket.send_bytes(message)
                else:
                    await websocket.send_text(str(message))
                return True
            except Exception as e:
                logger.error(f"Error sending to {connection_id}: {e}")
                # Remove broken connection
                await self.remove_connection(connection_id)
                return False
    
    async def broadcast_to_group(self, group_id: str, message: Union[str, bytes, Dict[str, Any]]):
        """Broadcast a message to all connections in a group"""
        async with self._lock:
            if group_id not in self.groups:
                return
            
            connections = self.groups[group_id].copy()
        
        # Send to each connection (outside of lock to avoid blocking)
        tasks = []
        for connection_id in connections:
            tasks.append(self.send_to_connection(connection_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_all(self, message: Union[str, bytes, Dict[str, Any]]):
        """Broadcast a message to all connections"""
        async with self._lock:
            connection_ids = list(self.connections.keys())
        
        # Send to each connection (outside of lock to avoid blocking)
        tasks = []
        for connection_id in connection_ids:
            tasks.append(self.send_to_connection(connection_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_connection_count(self) -> int:
        """Get the total number of active connections"""
        async with self._lock:
            return len(self.connections)
    
    async def get_group_count(self, group_id: str) -> int:
        """Get the number of connections in a group"""
        async with self._lock:
            return len(self.groups.get(group_id, []))
    
    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection"""
        async with self._lock:
            if connection_id not in self.connections:
                return None
            
            websocket = self.connections[connection_id]
            return {
                "id": connection_id,
                "path": websocket.path,
                "client": websocket.client,
                "state": websocket.state.name,
                "headers": websocket.headers
            }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()