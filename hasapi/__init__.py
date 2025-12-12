"""
HasAPI - Modern Python web framework for AI-native APIs

The fastest Python API framework with first-class AI support.
"""

__version__ = "0.0.1"
__author__ = "HasAPI Team"
__email__ = "team@hasapi.dev"

from .app import HasAPI
from .router import Route
from .response import JSONResponse, StreamingResponse
from .middleware import Middleware, CORSMiddleware
from .websocket import WebSocket, WebSocketDisconnect
from .openapi import api_doc, request_body, response, requires_auth

# UI components imports
from .ui import UI, Textbox, Slider, Number, Button, Text

# Template engine imports
from .templates import (
    Template, html, TemplateResponse, Layout,
    default_layout, dark_layout, minimal_layout
)

__all__ = [
    "HasAPI",
    "Route",
    "JSONResponse",
    "StreamingResponse",
    "Middleware",
    "CORSMiddleware",
    "WebSocket",
    "WebSocketDisconnect",
    "api_doc",
    "request_body",
    "response",
    "requires_auth",
    # Template engine exports
    "Template",
    "html",
    "TemplateResponse",
    "Layout",
    "default_layout",
    "dark_layout",
    "minimal_layout",
    # UI component exports
    "UI",
    "Textbox",
    "Slider",
    "Number",
    "Button",
    "Text",
]

# AI modules - lazy import to avoid heavy dependencies
def _lazy_import_ai():
    try:
        from .ai.llm import LLM
        from .ai.rag import RAG
        from .ai.embeddings import Embeddings
        from .ai.chat_memory import ChatMemory, ConversationManager
        return {
            "LLM": LLM,
            "RAG": RAG,
            "Embeddings": Embeddings,
            "ChatMemory": ChatMemory,
            "ConversationManager": ConversationManager
        }
    except ImportError:
        return {}

# Make AI modules available when dependencies are installed
_ai_modules = _lazy_import_ai()
for name, module in _ai_modules.items():
    globals()[name] = module
    __all__.append(name)
