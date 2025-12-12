"""
HasAPI Chat Memory Module

Conversation management for chat applications with pluggable storage backends.
Supports in-memory storage (default) and can be extended for SQLite, PostgreSQL, etc.
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        return f"{self.role}: {self.content}"


class ChatMemoryBackend(ABC):
    """Abstract base class for chat memory storage backends"""
    
    @abstractmethod
    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        """Add a message to a conversation"""
        pass
    
    @abstractmethod
    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get messages from a conversation"""
        pass
    
    @abstractmethod
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear all messages in a conversation"""
        pass
    
    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        pass
    
    @abstractmethod
    def list_conversations(self) -> List[str]:
        """List all conversation IDs"""
        pass


class InMemoryChatBackend(ChatMemoryBackend):
    """In-memory storage backend for chat messages"""
    
    def __init__(self):
        self.conversations: Dict[str, List[ChatMessage]] = {}
    
    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append(message)
    
    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        messages = self.conversations.get(conversation_id, [])
        if limit is None:
            return messages.copy()
        return messages[-limit:] if limit > 0 else []
    
    def clear_conversation(self, conversation_id: str) -> None:
        if conversation_id in self.conversations:
            self.conversations[conversation_id].clear()
    
    def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def list_conversations(self) -> List[str]:
        return list(self.conversations.keys())


class ChatMemory:
    """
    Chat conversation management with pluggable storage backends.
    
    Provides functionality to store, retrieve, and manage chat messages
    with conversation history and context window management.
    
    Supports multiple storage backends:
    - In-memory (default)
    - SQLite (future)
    - PostgreSQL (future)
    - Redis (future)
    """
    
    def __init__(
        self,
        conversation_id: str,
        backend: Optional[ChatMemoryBackend] = None,
        max_messages: int = 100,
        max_context: int = 10
    ):
        """
        Initialize chat memory.
        
        Args:
            conversation_id: Unique conversation identifier
            backend: Storage backend (defaults to in-memory)
            max_messages: Maximum number of messages to store per conversation
            max_context: Maximum number of messages to include in context
        """
        self.conversation_id = conversation_id
        self.backend = backend or InMemoryChatBackend()
        self.max_messages = max_messages
        self.max_context = max_context
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """
        Add a message to the conversation.
        
        Args:
            role: Message role (user, assistant, system, etc.)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            The created message
        """
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.backend.add_message(self.conversation_id, message)
        
        # Trim if exceeding max messages
        messages = self.backend.get_messages(self.conversation_id)
        if len(messages) > self.max_messages:
            # Clear and re-add only the last max_messages
            self.backend.clear_conversation(self.conversation_id)
            for msg in messages[-self.max_messages:]:
                self.backend.add_message(self.conversation_id, msg)
        
        return message
    
    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get messages from the conversation.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        return self.backend.get_messages(self.conversation_id, limit)
    
    def get_context(self, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get messages formatted for LLM context.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            List of message dictionaries for LLM
        """
        # Get recent messages for context
        context_messages = self.get_messages(self.max_context)
        
        # Filter and format
        formatted_messages = []
        for msg in context_messages:
            if msg.role == "system" and not include_system:
                continue
            
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return formatted_messages
    
    def get_last_message(self, role: Optional[str] = None) -> Optional[ChatMessage]:
        """
        Get the last message, optionally filtered by role.
        
        Args:
            role: Optional role to filter by
            
        Returns:
            The last message or None
        """
        messages = self.backend.get_messages(self.conversation_id)
        
        if not messages:
            return None
        
        if role is None:
            return messages[-1]
        
        # Find last message with specified role
        for msg in reversed(messages):
            if msg.role == role:
                return msg
        
        return None
    
    def clear(self):
        """Clear all messages in this conversation"""
        self.backend.clear_conversation(self.conversation_id)
        logger.info(f"Chat memory cleared for conversation: {self.conversation_id}")
    
    def trim_to_last(self, n: int):
        """
        Keep only the last n messages.
        
        Args:
            n: Number of messages to keep
        """
        messages = self.backend.get_messages(self.conversation_id)
        
        if n >= 0:
            trimmed = messages[-n:]
        else:
            trimmed = []
        
        self.backend.clear_conversation(self.conversation_id)
        for msg in trimmed:
            self.backend.add_message(self.conversation_id, msg)
        
        logger.info(f"Chat memory trimmed to last {n} messages for conversation: {self.conversation_id}")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        messages = self.backend.get_messages(self.conversation_id)
        
        if not messages:
            return {
                "conversation_id": self.conversation_id,
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "system_messages": 0
            }
        
        user_count = sum(1 for msg in messages if msg.role == "user")
        assistant_count = sum(1 for msg in messages if msg.role == "assistant")
        system_count = sum(1 for msg in messages if msg.role == "system")
        
        # Get time range
        timestamps = [msg.timestamp for msg in messages]
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration = end_time - start_time
        
        return {
            "conversation_id": self.conversation_id,
            "total_messages": len(messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "system_messages": system_count,
            "duration_seconds": duration,
            "start_time": start_time,
            "end_time": end_time
        }
    
    def export_conversation(self, format: str = "dict") -> Any:
        """
        Export the conversation in various formats.
        
        Args:
            format: Export format ("dict", "json", "txt")
            
        Returns:
            Exported conversation data
        """
        messages = self.backend.get_messages(self.conversation_id)
        
        if format == "dict":
            return [msg.to_dict() for msg in messages]
        
        elif format == "json":
            import json
            return json.dumps([msg.to_dict() for msg in messages], indent=2)
        
        elif format == "txt":
            lines = []
            for msg in messages:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg.timestamp))
                lines.append(f"[{timestamp}] {msg.role}: {msg.content}")
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def load_conversation(self, data: Any, format: str = "dict"):
        """
        Load conversation data from various formats.
        
        Args:
            data: Conversation data
            format: Data format ("dict", "json", "txt")
        """
        self.clear()
        
        if format == "dict":
            for msg_data in data:
                message = ChatMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data.get("timestamp", time.time()),
                    metadata=msg_data.get("metadata", {})
                )
                self.backend.add_message(self.conversation_id, message)
        
        elif format == "json":
            import json
            msg_data = json.loads(data)
            self.load_conversation(msg_data, "dict")
        
        elif format == "txt":
            lines = data.split("\n")
            for line in lines:
                if line.strip():
                    # Parse format: [timestamp] role: content
                    try:
                        if line.startswith("[") and "] " in line:
                            timestamp_part, rest = line.split("] ", 1)
                            role_content = rest.split(": ", 1)
                            if len(role_content) == 2:
                                role, content = role_content
                                self.add_message(role, content)
                    except:
                        # Fallback: treat entire line as content
                        self.add_message("user", line)
        
        else:
            raise ValueError(f"Unsupported import format: {format}")
        
        messages = self.backend.get_messages(self.conversation_id)
        logger.info(f"Loaded {len(messages)} messages from {format} format for conversation: {self.conversation_id}")
    
    def search_messages(self, query: str, role: Optional[str] = None) -> List[ChatMessage]:
        """
        Search messages by content.
        
        Args:
            query: Search query
            role: Optional role to filter by
            
        Returns:
            List of matching messages
        """
        messages = self.backend.get_messages(self.conversation_id)
        query_lower = query.lower()
        matching_messages = []
        
        for msg in messages:
            if role and msg.role != role:
                continue
            
            if query_lower in msg.content.lower():
                matching_messages.append(msg)
        
        return matching_messages
    
    def get_token_count_estimate(self) -> int:
        """
        Estimate total token count of the conversation.
        
        Returns:
            Estimated token count (rough approximation)
        """
        messages = self.backend.get_messages(self.conversation_id)
        total_chars = sum(len(msg.content) for msg in messages)
        # Rough approximation: ~4 characters per token
        return total_chars // 4


class ConversationManager:
    """
    Manages multiple conversations with session support and shared storage backend.
    """
    
    def __init__(self, backend: Optional[ChatMemoryBackend] = None):
        """
        Initialize conversation manager.
        
        Args:
            backend: Shared storage backend for all conversations (defaults to in-memory)
        """
        self.backend = backend or InMemoryChatBackend()
        self.conversations: Dict[str, ChatMemory] = {}
        self.active_conversation: Optional[str] = None
    
    def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        max_messages: int = 100,
        max_context: int = 10
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Optional conversation ID (auto-generated if not provided)
            max_messages: Maximum messages to store
            max_context: Maximum messages in context window
            
        Returns:
            Conversation ID
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        self.conversations[conversation_id] = ChatMemory(
            conversation_id=conversation_id,
            backend=self.backend,
            max_messages=max_messages,
            max_context=max_context
        )
        self.active_conversation = conversation_id
        
        logger.info(f"Created new conversation: {conversation_id}")
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[ChatMemory]:
        """
        Get a conversation by ID. Creates it if it doesn't exist.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Chat memory instance
        """
        if conversation_id not in self.conversations:
            # Check if conversation exists in backend
            if conversation_id in self.backend.list_conversations():
                self.conversations[conversation_id] = ChatMemory(
                    conversation_id=conversation_id,
                    backend=self.backend
                )
            else:
                return None
        
        return self.conversations.get(conversation_id)
    
    def get_or_create_conversation(self, conversation_id: str) -> ChatMemory:
        """
        Get a conversation by ID, creating it if it doesn't exist.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Chat memory instance
        """
        conv = self.get_conversation(conversation_id)
        if conv is None:
            self.create_conversation(conversation_id)
            conv = self.conversations[conversation_id]
        return conv
    
    def set_active_conversation(self, conversation_id: str):
        """
        Set the active conversation.
        
        Args:
            conversation_id: Conversation ID to set as active
        """
        if conversation_id in self.conversations:
            self.active_conversation = conversation_id
            logger.info(f"Set active conversation: {conversation_id}")
        else:
            logger.warning(f"Conversation not found: {conversation_id}")
    
    def get_active_conversation(self) -> Optional[ChatMemory]:
        """
        Get the active conversation.
        
        Returns:
            Active chat memory or None
        """
        if self.active_conversation:
            return self.conversations.get(self.active_conversation)
        return None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation from both memory and backend.
        
        Args:
            conversation_id: Conversation ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        
        # Remove from backend
        deleted = self.backend.delete_conversation(conversation_id)
        
        # Clear active if it was the deleted one
        if self.active_conversation == conversation_id:
            self.active_conversation = None
        
        if deleted:
            logger.info(f"Deleted conversation: {conversation_id}")
        
        return deleted
    
    def list_conversations(self) -> List[str]:
        """
        List all conversation IDs from backend.
        
        Returns:
            List of conversation IDs
        """
        return self.backend.list_conversations()
    
    def get_conversation_summaries(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summaries of all conversations.
        
        Returns:
            Dictionary mapping conversation IDs to summaries
        """
        summaries = {}
        for conv_id in self.backend.list_conversations():
            conv = self.get_or_create_conversation(conv_id)
            summaries[conv_id] = conv.get_conversation_summary()
        return summaries