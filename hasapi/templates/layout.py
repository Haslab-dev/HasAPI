"""
Simplified Layout System

Minimal layout system with Tailwind CSS support.
"""

from typing import Optional, Dict, Any


class Layout:
    """Layout with Tailwind CSS"""
    
    def __init__(
        self,
        title: str = "HasAPI App",
        theme: str = "default",
        custom_css: str = "",
        custom_js: str = ""
    ):
        self.title = title
        self.theme = theme
        self.custom_css = custom_css
        self.custom_js = custom_js
    
    def get_css(self) -> str:
        """Get CSS for the layout"""
        css = '<script src="https://cdn.tailwindcss.com"></script>'
        
        # Add theme-specific CSS
        if self.theme == "dark":
            css += """
<style>
body { background-color: #1a202c; color: #e2e8f0; }
.card { background-color: #2d3748; border-color: #4a5568; }
</style>
"""
        elif self.theme == "minimal":
            css += """
<style>
body { font-family: system-ui, sans-serif; }
.card { border: 1px solid #e2e8f0; }
</style>
"""
        
        if self.custom_css:
            css += f"<style>{self.custom_css}</style>"
        
        return css
    
    def get_js(self) -> str:
        """Get JavaScript for the layout"""
        if not self.custom_js:
            return ""
        
        return f"<script>{self.custom_js}</script>"
    
    def wrap(self, content: str) -> str:
        """Wrap content in a complete HTML page"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    {self.get_css()}
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        {content}
    </div>
    {self.get_js()}
</body>
</html>"""


# Predefined layouts
def default_layout(title: str = "HasAPI App", **kwargs) -> Layout:
    """Default layout with standard styling"""
    return Layout(title=title, **kwargs)


def dark_layout(title: str = "HasAPI App", **kwargs) -> Layout:
    """Dark theme layout"""
    return Layout(title=title, theme="dark", **kwargs)


def minimal_layout(title: str = "HasAPI App", **kwargs) -> Layout:
    """Minimal layout with no extra styling"""
    return Layout(title=title, theme="minimal", **kwargs)