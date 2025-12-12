"""
HasAPI Templating Engine

A minimal template system with server-side rendering and simple client-side interactivity.
"""

from .engine import Template, html, HTMLBuilder
from .response import TemplateResponse, TemplateJSONResponse
from .layout import Layout, default_layout, dark_layout, minimal_layout

__all__ = [
    "Template",
    "html",
    "HTMLBuilder",
    "TemplateResponse",
    "TemplateJSONResponse",
    "Layout",
    "default_layout",
    "dark_layout",
    "minimal_layout"
]