"""
Simplified UI Components

Minimal components with essential properties only.
"""

from typing import Any, Optional, List, Union
from ..templates.engine import html


class Component:
    """Base component with minimal properties"""
    
    def __init__(
        self,
        label: Optional[str] = None,
        value: Any = None,
        id: Optional[str] = None
    ):
        self.label = label
        self.value = value
        self.id = id
    
    def render_input(self) -> str:
        """Render component as input element"""
        raise NotImplementedError("Subclasses must implement render_input")
    
    def render_output(self) -> str:
        """Render component as output element"""
        raise NotImplementedError("Subclasses must implement render_output")


class Textbox(Component):
    """Text input component"""
    
    def __init__(
        self,
        label: Optional[str] = None,
        value: str = "",
        lines: int = 1,
        placeholder: Optional[str] = None,
        **kwargs
    ):
        super().__init__(label=label, value=value, **kwargs)
        self.lines = lines
        self.placeholder = placeholder
    
    def render_input(self) -> str:
        """Render textbox as input"""
        base_classes = "w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        
        if self.lines > 1:
            return html.div(
                [
                    html.label(
                        self.label or "Input",
                        **{"class": "block text-sm font-medium text-gray-700 mb-2", "for": self.id}
                    ),
                    html.textarea(
                        self.value or "",
                        **{
                            "id": self.id,
                            "class": base_classes,
                            "placeholder": self.placeholder or "",
                            "rows": str(self.lines)
                        }
                    )
                ],
                **{"class": "mb-4"}
            )
        else:
            return html.div(
                [
                    html.label(
                        self.label or "Input",
                        **{"class": "block text-sm font-medium text-gray-700 mb-2", "for": self.id}
                    ),
                    html.input(**{
                        "type": "text",
                        "id": self.id,
                        "class": base_classes,
                        "placeholder": self.placeholder or "",
                        "value": self.value or ""
                    })
                ],
                **{"class": "mb-4"}
            )
    
    def render_output(self) -> str:
        """Render textbox as output display"""
        return html.div(
            {"class": "mb-4"},
            html.label(
                {"class": "block text-sm font-medium text-gray-700 mb-2"},
                self.label or "Output"
            ),
            html.div({
                "id": self.id,
                "class": "p-3 bg-gray-50 border border-gray-200 rounded-lg min-h-[80px] text-gray-800"
            }, "Output will appear here...")
        )


class Slider(Component):
    """Slider component for numeric values"""
    
    def __init__(
        self,
        minimum: float = 0,
        maximum: float = 100,
        value: float = 50,
        step: Optional[float] = None,
        label: Optional[str] = None,
        **kwargs
    ):
        super().__init__(label=label, value=value, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step or 1
    
    def render_input(self) -> str:
        """Render slider as input"""
        return html.div(
            [
                html.label(
                    self.label or "Slider",
                    **{"class": "block text-sm font-medium text-gray-700 mb-2", "for": self.id}
                ),
                html.input(**{
                    "type": "range",
                    "id": self.id,
                    "class": "w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer",
                    "min": str(self.minimum),
                    "max": str(self.maximum),
                    "step": str(self.step),
                    "value": str(self.value)
                }),
                html.div(
                    [
                        html.span(str(self.minimum)),
                        html.span(str(self.value), **{"id": f"{self.id}_value"}),
                        html.span(str(self.maximum))
                    ],
                    **{"class": "flex justify-between text-sm text-gray-500 mt-1"}
                )
            ],
            **{"class": "mb-4"}
        )
    
    def render_output(self) -> str:
        """Render slider as output display"""
        return html.div(
            {"class": "mb-4"},
            html.label(
                {"class": "block text-sm font-medium text-gray-700 mb-2"},
                self.label or "Value"
            ),
            html.div({
                "id": self.id,
                "class": "p-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-800"
            }, str(self.value))
        )


class Number(Component):
    """Number input component"""
    
    def __init__(
        self,
        value: float = 0,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        step: Optional[float] = None,
        label: Optional[str] = None,
        **kwargs
    ):
        super().__init__(label=label, value=value, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
    
    def render_input(self) -> str:
        """Render number as input"""
        input_attrs = {
            "type": "number",
            "id": self.id,
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
            "value": str(self.value)
        }
        
        if self.minimum is not None:
            input_attrs["min"] = str(self.minimum)
        if self.maximum is not None:
            input_attrs["max"] = str(self.maximum)
        if self.step is not None:
            input_attrs["step"] = str(self.step)
        
        return html.div(
            [
                html.label(
                    self.label or "Number",
                    **{"class": "block text-sm font-medium text-gray-700 mb-2", "for": self.id}
                ),
                html.input(**input_attrs)
            ],
            **{"class": "mb-4"}
        )
    
    def render_output(self) -> str:
        """Render number as output display"""
        return html.div(
            [
                html.label(
                    self.label or "Number",
                    **{"class": "block text-sm font-medium text-gray-700 mb-2"}
                ),
                html.div(
                    str(self.value),
                    **{
                        "id": self.id,
                        "class": "p-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-800"
                    }
                )
            ],
            **{"class": "mb-4"}
        )


class Button(Component):
    """Button component"""
    
    def __init__(
        self,
        value: str = "Button",
        variant: str = "primary",
        size: str = "medium",
        **kwargs
    ):
        super().__init__(value=value, **kwargs)
        self.variant = variant
        self.size = size
    
    def render_input(self) -> str:
        """Render button as input"""
        # Button styles
        variant_classes = {
            "primary": "bg-blue-600 hover:bg-blue-700",
            "secondary": "bg-gray-600 hover:bg-gray-700",
            "success": "bg-green-600 hover:bg-green-700",
            "danger": "bg-red-600 hover:bg-red-700"
        }
        
        size_classes = {
            "small": "px-3 py-1.5 text-sm",
            "medium": "px-4 py-2 text-base",
            "large": "px-6 py-3 text-lg"
        }
        
        button_class = f"text-white font-medium rounded-lg transition-colors {variant_classes.get(self.variant, variant_classes['primary'])} {size_classes.get(self.size, size_classes['medium'])}"
        
        return html.button(
            self.value,
            **{
                "id": self.id,
                "class": button_class
            }
        )
    
    def render_output(self) -> str:
        """Buttons don't have output display"""
        return ""


class Text(Component):
    """Text display component"""
    
    def __init__(
        self,
        value: str = "",
        label: Optional[str] = None,
        **kwargs
    ):
        super().__init__(label=label, value=value, **kwargs)
    
    def render_input(self) -> str:
        """Text doesn't have input"""
        return ""
    
    def render_output(self) -> str:
        """Render text as output"""
        return html.div(
            [
                html.label(
                    self.label or "Text",
                    **{"class": "block text-sm font-medium text-gray-700 mb-2"}
                ),
                html.div(
                    self.value or "No text",
                    **{
                        "id": self.id,
                        "class": "p-3 bg-gray-50 border border-gray-200 rounded-lg min-h-[80px] text-gray-800"
                    }
                )
            ],
            **{"class": "mb-4"}
        )