"""
Simplified Block UI Core

Main UI class with Gradio-like interface.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Callable, Union
from ..templates.engine import html
from ..templates.response import TemplateResponse
from ..templates.layout import default_layout
from .components import Textbox, Text, Slider, Number


class UI:
    """
    UI Interface - Like Gradio
    
    Creates a clean UI around a Python function with input and output components.
    Minimal design with server-side processing.
    """
    
    def __init__(
        self,
        fn: Callable,
        inputs: Union['Component', List['Component']] = None,
        outputs: Union['Component', List['Component']] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        theme: str = "default",
        api_name: Optional[str] = None
    ):
        self.fn = fn
        self.title = title or fn.__name__.replace("_", " ").title()
        self.description = description
        self.theme = theme
        self.api_name = api_name or fn.__name__
        
        # Normalize inputs and outputs to lists
        self.inputs = inputs if isinstance(inputs, list) else [inputs] if inputs else []
        self.outputs = outputs if isinstance(outputs, list) else [outputs] if outputs else []
        
        # Add default components if none provided
        if not self.inputs:
            self.inputs = [Textbox(label="Input")]
        if not self.outputs:
            self.outputs = [Text(label="Output")]
        
        # Generate unique IDs for components
        self._generate_ids()
    
    def _generate_ids(self):
        """Generate unique IDs for all components"""
        for i, component in enumerate(self.inputs):
            component.id = component.id or f"input_{i}"
        
        for i, component in enumerate(self.outputs):
            component.id = component.id or f"output_{i}"
    
    def _render_template(self) -> str:
        """Render the UI template"""
        elements = []
        
        # Header
        if self.title:
            elements.append(html.h1(
                self.title,
                **{"class": "text-3xl font-bold text-gray-900 mb-2 text-center"}
            ))
        
        if self.description:
            elements.append(html.p(
                self.description,
                **{"class": "text-gray-600 mb-6 text-center"}
            ))
        
        # Main container
        container_elements = []
        
        # Input section
        if self.inputs:
            input_elements = []
            for component in self.inputs:
                input_elements.append(component.render_input())
            
            container_elements.append(html.div(
                [
                    html.h3("Input", **{"class": "text-lg font-semibold mb-4"}),
                    *input_elements
                ],
                **{"class": "bg-white rounded-lg shadow p-6 mb-6"}
            ))
        
        # Submit button
        container_elements.append(html.button(
            "Submit",
            **{
                "class": "w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors mb-6",
                "onclick": "submitForm()",
                "id": "submit-btn"
            }
        ))
        
        # Output section
        if self.outputs:
            output_elements = []
            for component in self.outputs:
                output_elements.append(component.render_output())
            
            container_elements.append(html.div(
                [
                    html.h3("Output", **{"class": "text-lg font-semibold mb-4"}),
                    *output_elements
                ],
                **{"class": "bg-white rounded-lg shadow p-6"}
            ))
        
        elements.append(html.div(
            container_elements,
            **{"class": "max-w-2xl mx-auto"}
        ))
        
        return html.div(
            elements,
            **{"class": "min-h-screen bg-gray-50 py-8 px-4"}
        )
    
    def _get_javascript(self) -> str:
        """Get JavaScript for the UI"""
        return f"""
async function submitForm() {{
    const submitBtn = document.getElementById('submit-btn');
    const originalText = submitBtn.textContent;
    
    try {{
        submitBtn.textContent = 'Processing...';
        submitBtn.disabled = true;
        
        // Collect input values
        const inputData = {{}};
        {self._get_input_collection_js()}
        
        // Call API
        const response = await fetch('/api/{self.api_name}', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(inputData)
        }});
        
        const result = await response.json();
        
        // Update outputs
        if (result.success) {{
            {self._get_output_update_js()}
        }} else {{
            const firstOutput = document.querySelector('[id^="output_"]');
            if (firstOutput) {{
                firstOutput.textContent = 'Error: ' + result.error;
                firstOutput.style.color = 'red';
            }}
        }}
    }} catch (error) {{
        const firstOutput = document.querySelector('[id^="output_"]');
        if (firstOutput) {{
            firstOutput.textContent = 'Network Error: ' + error.message;
            firstOutput.style.color = 'red';
        }}
    }} finally {{
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }}
}}

// Update slider values
document.addEventListener('DOMContentLoaded', () => {{
    const sliders = document.querySelectorAll('input[type="range"]');
    sliders.forEach(slider => {{
        const valueDisplay = document.getElementById(slider.id + '_value');
        if (valueDisplay) {{
            slider.addEventListener('input', () => {{
                valueDisplay.textContent = slider.value;
            }});
        }}
    }});
}});
"""
    
    def _get_input_collection_js(self) -> str:
        """Generate JavaScript for collecting input values"""
        js_parts = []
        for i, component in enumerate(self.inputs):
            if isinstance(component, Slider):
                js_parts.append(f"""
                inputData['input_{i}'] = parseFloat(document.getElementById('input_{i}').value) || 0;""")

            else:
                js_parts.append(f"""
                inputData['input_{i}'] = document.getElementById('input_{i}').value || '';""")
        
        return '\n'.join(js_parts)
    
    def _get_output_update_js(self) -> str:
        """Generate JavaScript for updating output values"""
        js_parts = []
        for i in range(len(self.outputs)):
            js_parts.append(f"""
            const outputEl{i} = document.getElementById('output_{i}');
            if (outputEl{i}) {{
                outputEl{i}.textContent = result.data['output_{i}'];
                outputEl{i}.style.color = '';
            }}""")
        
        return '\n'.join(js_parts)
    
    def _setup_api_endpoint(self, app):
        """Setup API endpoint for the interface"""
        from ..response import JSONResponse
        
        @app.post(f"/api/{self.api_name}")
        async def api_predict(request):
            try:
                data = await request.json()
                
                # Extract input values
                input_values = []
                for i, component in enumerate(self.inputs):
                    value = data.get(f"input_{i}", "")
                    
                    # Convert value based on component type
                    if isinstance(component, Slider) or isinstance(component, Number):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = component.value or 0

                    
                    input_values.append(value)
                
                # Call Python function
                result = self.fn(*input_values)
                
                # Handle multiple outputs
                if len(self.outputs) > 1:
                    if not isinstance(result, (list, tuple)):
                        result = [result]
                    output_dict = {}
                    for i, output in enumerate(result):
                        output_dict[f"output_{i}"] = str(output)
                    response_data = {"success": True, "data": output_dict}
                else:
                    response_data = {"success": True, "data": {"output_0": str(result)}}
                
                return JSONResponse(response_data)
            
            except Exception as e:
                return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    
    def launch(
        self,
        app=None,
        server_port: int = 7860,
        prevent_thread_lock: bool = False,
        **kwargs
    ):
        """Launch the UI interface"""
        from ..app import HasAPI
        
        # Create app if not provided
        if app is None:
            app = HasAPI(debug=True)
        
        # Setup API endpoint
        self._setup_api_endpoint(app)
        
        # Setup main route
        @app.get("/")
        async def index(request):
            layout = default_layout(self.title)
            template = self._render_template()
            return TemplateResponse(
                template_string=layout.wrap(template),
                title=self.title,
                custom_js=self._get_javascript()
            )
        
        # Launch server if not preventing thread lock
        if not prevent_thread_lock:
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=server_port)
        
        return app