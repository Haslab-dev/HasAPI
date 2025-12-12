"""
Simplified Template Engine

A minimal template engine with server-side rendering and simple client-side interactivity.
"""

import os
import json
from typing import Dict, Any, Optional, Callable, Union
from pathlib import Path


class Template:
    """
    Template engine with server-side rendering.
    
    Focus on simplicity and performance with minimal JavaScript.
    """
    
    def __init__(self, app=None):
        self.app = app
        self.routes = {}
        self.static_files = {}
        self.global_context = {}
        
    def route(self, path: str, template_path: Optional[str] = None):
        """Decorator to register a template route"""
        def decorator(func):
            async def wrapper(request):
                # Execute the function to get context
                context = await func(request) if callable(func) else func
                
                # If template_path is provided, render template
                if template_path:
                    html_content = self.render_template(template_path, context)
                    # Import HTMLResponse here to avoid circular imports
                    from ..response import HTMLResponse
                    return HTMLResponse(html_content)
                else:
                    # Assume function returns a response object or HTML string
                    return context
                    
            # Register route with app
            if self.app:
                self.app.get(path)(wrapper)
            self.routes[path] = wrapper
            return wrapper
        return decorator
    
    def render_template(self, template_path: str, context: Dict[str, Any] = None) -> str:
        """
        Render a template with context.
        
        Uses Python f-string style templating for simplicity.
        """
        context = context or {}
        context.update(self.global_context)
        
        # Read template file
        template_file = Path(template_path)
        if not template_file.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        template_content = template_file.read_text()
        
        # Simple f-string style templating
        try:
            return template_content.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing context variable: {e}")
    
    def render_string(self, template_string: str, context: Dict[str, Any] = None) -> str:
        """Render a template string with context"""
        context = context or {}
        context.update(self.global_context)
        
        try:
            return template_string.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing context variable: {e}")
    
    def static(self, prefix: str, directory: str):
        """Register static file serving"""
        static_path = Path(directory)
        
        async def serve_static(request):
            # Get the file path from the request
            file_path = static_path / request.path_params.get('filename', '')
            
            if not file_path.exists() or not file_path.is_file():
                return {"error": "File not found"}, 404
            
            # Get file extension and content type
            ext = file_path.suffix.lower()
            content_types = {
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.html': 'text/html',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon'
            }
            
            content_type = content_types.get(ext, 'application/octet-stream')
            
            # Read and return file content
            content = file_path.read_bytes()
            return {
                "content": content,
                "content_type": content_type
            }
        
        # Register static route
        if self.app:
            pattern = f"{prefix}/{{filename:path}}"
            self.app.get(pattern)(serve_static)
        
        self.static_files[prefix] = directory
    
    def add_global(self, name: str, value: Any):
        """Add a global context variable available to all templates"""
        self.global_context[name] = value


class HTMLBuilder:
    """Simple HTML builder for creating elements programmatically"""
    
    @staticmethod
    def tag(tag_name: str, content: Union[str, list] = "", **attrs) -> str:
        """Create an HTML tag with attributes and content"""
        # Convert attributes to HTML attributes
        attr_str = ""
        for key, value in attrs.items():
            # Convert underscores to hyphens for HTML attributes
            html_key = key.replace('_', '-')
            
            if value is True:
                attr_str += f' {html_key}'
            elif value is not False and value is not None:
                # Handle special cases
                if html_key == 'class_':
                    html_key = 'class'
                elif html_key == 'for_':
                    html_key = 'for'
                    
                attr_str += f' {html_key}="{value}"'
        
        # Handle content
        if isinstance(content, list):
            content = ''.join(str(item) for item in content)
        
        # Self-closing tags
        if tag_name in ['br', 'hr', 'img', 'input', 'meta', 'link']:
            return f'<{tag_name}{attr_str} />'
        
        return f'<{tag_name}{attr_str}>{content}</{tag_name}>'
    
    @staticmethod
    def div(content="", **attrs):
        """Create a div element"""
        return HTMLBuilder.tag('div', content, **attrs)
    
    @staticmethod
    def span(content="", **attrs):
        """Create a span element"""
        return HTMLBuilder.tag('span', content, **attrs)
    
    @staticmethod
    def button(content="", **attrs):
        """Create a button element"""
        return HTMLBuilder.tag('button', content, **attrs)
    
    @staticmethod
    def input(**attrs):
        """Create an input element"""
        return HTMLBuilder.tag('input', **attrs)
    
    @staticmethod
    def textarea(content="", **attrs):
        """Create a textarea element"""
        return HTMLBuilder.tag('textarea', content, **attrs)
    
    @staticmethod
    def select(options: list = [], **attrs):
        """Create a select element with options"""
        option_tags = []
        for option in options:
            if isinstance(option, tuple):
                value, label = option
                option_tags.append(HTMLBuilder.tag('option', label, value=value))
            else:
                option_tags.append(HTMLBuilder.tag('option', option, value=option))
        
        return HTMLBuilder.tag('select', option_tags, **attrs)
    
    @staticmethod
    def label(content="", **attrs):
        """Create a label element"""
        return HTMLBuilder.tag('label', content, **attrs)
    
    @staticmethod
    def h1(content="", **attrs):
        """Create an h1 element"""
        return HTMLBuilder.tag('h1', content, **attrs)
    
    @staticmethod
    def h2(content="", **attrs):
        """Create an h2 element"""
        return HTMLBuilder.tag('h2', content, **attrs)
    
    @staticmethod
    def h3(content="", **attrs):
        """Create an h3 element"""
        return HTMLBuilder.tag('h3', content, **attrs)
    
    @staticmethod
    def p(content="", **attrs):
        """Create a p element"""
        return HTMLBuilder.tag('p', content, **attrs)
    
    @staticmethod
    def a(content="", href="", **attrs):
        """Create an a element"""
        return HTMLBuilder.tag('a', content, href=href, **attrs)
    
    @staticmethod
    def img(src="", alt="", **attrs):
        """Create an img element"""
        return HTMLBuilder.tag('img', src=src, alt=alt, **attrs)
    
    @staticmethod
    def script(content="", src="", **attrs):
        """Create a script element"""
        if src:
            return HTMLBuilder.tag('script', '', src=src, **attrs)
        else:
            return HTMLBuilder.tag('script', content, **attrs)
    
    @staticmethod
    def style(content="", **attrs):
        """Create a style element"""
        return HTMLBuilder.tag('style', content, **attrs)
    
    @staticmethod
    def link(href="", rel="stylesheet", **attrs):
        """Create a link element"""
        return HTMLBuilder.tag('link', '', href=href, rel=rel, **attrs)
    
    @staticmethod
    def ul(content="", **attrs):
        """Create a ul element"""
        return HTMLBuilder.tag('ul', content, **attrs)
    
    @staticmethod
    def li(content="", **attrs):
        """Create a li element"""
        return HTMLBuilder.tag('li', content, **attrs)


# Global HTML builder instance
html = HTMLBuilder()