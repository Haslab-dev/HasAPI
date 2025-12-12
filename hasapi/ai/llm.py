"""
HasAPI LLM Core

Unified interface for Large Language Models with support for multiple providers.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, Callable
from abc import ABC, abstractmethod

from ..utils import get_logger
from ..exceptions import DependencyError

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get a chat completion response"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion response"""
        pass
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate an image from a prompt"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise DependencyError("openai", "Install with: pip install hasapi[ai]")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get a chat completion from OpenAI"""
        try:
            # Build request parameters, excluding None values
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            response = await self.client.chat.completions.create(**params)
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason
            }
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {e}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion from OpenAI"""
        try:
            # Build request parameters, excluding None values
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                **kwargs
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            raise
    
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate an image using OpenAI DALL-E"""
        try:
            response = await self.client.images.generate(
                model=model or "dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                **kwargs
            )
            
            return {
                "url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt
            }
        except Exception as e:
            logger.error(f"OpenAI image generation error: {e}")
            raise


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise DependencyError("anthropic", "Install with: pip install hasapi[ai]")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get a chat completion from Claude"""
        try:
            # Convert OpenAI format to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            response = await self.client.messages.create(
                model=model,
                messages=claude_messages,
                system=system_message,
                temperature=temperature,
                max_tokens=max_tokens or 1024,
                **kwargs
            )
            
            return {
                "content": response.content[0].text,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else None,
                "model": response.model,
                "finish_reason": response.stop_reason
            }
        except Exception as e:
            logger.error(f"Claude chat completion error: {e}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion from Claude"""
        try:
            # Convert OpenAI format to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            stream = await self.client.messages.create(
                model=model,
                messages=claude_messages,
                system=system_message,
                temperature=temperature,
                max_tokens=max_tokens or 1024,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        yield chunk.delta.text
        except Exception as e:
            logger.error(f"Claude stream error: {e}")
            raise
    
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Claude doesn't support image generation"""
        raise NotImplementedError("Claude does not support image generation")


class CustomProvider(LLMProvider):
    """Custom LLM provider for implementing your own logic"""
    
    def __init__(self, chat_func: Callable, stream_func: Callable = None, image_func: Callable = None):
        """
        Initialize custom provider
        
        Args:
            chat_func: Function for chat completions
            stream_func: Function for streaming chat completions
            image_func: Function for image generation
        """
        self.chat_func = chat_func
        self.stream_func = stream_func
        self.image_func = image_func
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call the custom chat function"""
        if not self.chat_func:
            raise NotImplementedError("Chat completion not implemented")
        
        result = self.chat_func(messages, model, temperature, max_tokens, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Call the custom stream function"""
        if not self.stream_func:
            raise NotImplementedError("Streaming not implemented")
        
        result = self.stream_func(messages, model, temperature, max_tokens, **kwargs)
        if asyncio.iscoroutine(result):
            async for chunk in await result:
                yield chunk
        else:
            for chunk in result:
                yield chunk
    
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Call the custom image generation function"""
        if not self.image_func:
            raise NotImplementedError("Image generation not implemented")
        
        result = self.image_func(prompt, model, size, quality, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result


class LLM:
    """
    Unified LLM interface supporting multiple providers.
    
    Provides a simple API for chat completion, streaming, and image generation
    across different LLM providers like OpenAI and Claude.
    """
    
    def __init__(self, provider: str = "openai", **kwargs):
        """
        Initialize LLM with specified provider.
        
        Args:
            provider: Provider name ("openai", "claude", "custom")
            **kwargs: Provider-specific arguments
        """
        self.provider_name = provider
        self.provider = self._create_provider(provider, **kwargs)
    
    def _create_provider(self, provider: str, **kwargs) -> LLMProvider:
        """Create a provider instance"""
        if provider == "openai":
            api_key = kwargs.get("api_key")
            base_url = kwargs.get("base_url")
            if not api_key:
                raise ValueError("OpenAI provider requires 'api_key' parameter")
            return OpenAIProvider(api_key, base_url)
        
        elif provider == "claude":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("Claude provider requires 'api_key' parameter")
            return ClaudeProvider(api_key)
        
        elif provider == "custom":
            chat_func = kwargs.get("chat_func")
            stream_func = kwargs.get("stream_func")
            image_func = kwargs.get("image_func")
            if not chat_func:
                raise ValueError("Custom provider requires 'chat_func' parameter")
            return CustomProvider(chat_func, stream_func, image_func)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def chat(
        self,
        messages: List[Union[str, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a chat completion response.
        
        Args:
            messages: List of messages (strings or dicts with role/content)
            model: Model name (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Response dictionary with content and metadata
        """
        # Normalize messages to OpenAI format
        normalized_messages = self._normalize_messages(messages)
        
        # Use default model if not specified
        if not model:
            model = self._get_default_model()
        
        return await self.provider.chat_completion(
            normalized_messages,
            model,
            temperature,
            max_tokens,
            **kwargs
        )
    
    async def stream(
        self,
        messages: List[Union[str, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion response.
        
        Args:
            messages: List of messages (strings or dicts with role/content)
            model: Model name (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Response tokens as they are generated
        """
        # Normalize messages to OpenAI format
        normalized_messages = self._normalize_messages(messages)
        
        # Use default model if not specified
        if not model:
            model = self._get_default_model()
        
        async for token in self.provider.stream_chat_completion(
            normalized_messages,
            model,
            temperature,
            max_tokens,
            **kwargs
        ):
            yield token
    
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an image from a prompt.
        
        Args:
            prompt: Text prompt for image generation
            model: Model name (provider-specific)
            size: Image size
            quality: Image quality
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Response dictionary with image URL and metadata
        """
        return await self.provider.generate_image(
            prompt,
            model,
            size,
            quality,
            **kwargs
        )
    
    def _normalize_messages(self, messages: List[Union[str, Dict[str, str]]]) -> List[Dict[str, str]]:
        """Normalize messages to OpenAI format"""
        normalized = []
        
        for message in messages:
            if isinstance(message, str):
                normalized.append({"role": "user", "content": message})
            elif isinstance(message, dict):
                if "role" not in message or "content" not in message:
                    raise ValueError("Message dict must have 'role' and 'content' keys")
                normalized.append(message)
            else:
                raise ValueError("Message must be string or dict")
        
        return normalized
    
    def _get_default_model(self) -> str:
        """Get default model for the current provider"""
        defaults = {
            "openai": "gpt-3.5-turbo",
            "claude": "claude-3-sonnet-20240229",
            "custom": "custom"
        }
        return defaults.get(self.provider_name, "default")