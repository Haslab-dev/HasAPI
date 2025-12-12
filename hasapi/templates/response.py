"""
Simplified Template Response

Minimal response handling for the simplified template engine.
"""

import json
from typing import Dict, Any, Optional
from ..response import HTMLResponse


class TemplateResponse(HTMLResponse):
    """Template response with minimal JavaScript"""
    
    def __init__(
        self, 
        template_string: str, 
        context: Dict[str, Any] = None,
        title: str = "HasAPI App",
        include_tailwind: bool = True,
        custom_css: str = "",
        custom_js: str = ""
    ):
        self.template_string = template_string
        self.context = context or {}
        self.title = title
        self.include_tailwind = include_tailwind
        self.custom_css = custom_css
        self.custom_js = custom_js
        
        # Generate the complete HTML
        html_content = self._generate_html()
        
        # HTMLResponse expects bytes, so convert string to bytes
        super().__init__(html_content)
    
    def _generate_html(self) -> str:
        """Generate the complete HTML page"""
        # Render the main template with context
        try:
            content = self.template_string.format(**self.context)
        except KeyError as e:
            content = f"Error: Missing context variable {e}"
        
        # Build the complete HTML page
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    {self._get_css()}
</head>
<body>
    {content}
    {self._get_js()}
</body>
</html>"""
        
        return html
    
    def _get_css(self) -> str:
        """Get CSS for the page"""
        css = ""
        
        if self.include_tailwind:
            css += '<script src="https://cdn.tailwindcss.com"></script>'
        
        if self.custom_css:
            css += f"<style>{self.custom_css}</style>"
        
        return css
    
    def _get_js(self) -> str:
        """Get JavaScript for the page"""
        if not self.custom_js:
            return ""
        
        return f"<script>{self.custom_js}</script>"


class TemplateJSONResponse:
    """JSON response for template API endpoints"""
    
    def __init__(self, data: Any, status_code: int = 200):
        self.data = data
        self.status_code = status_code
    
    def to_response(self):
        """Convert to a response object"""
        from ..response import JSONResponse
        return JSONResponse(self.data, status_code=self.status_code)