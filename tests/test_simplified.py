"""
Test script for simplified HasAPI implementation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_template_engine():
    """Test the template engine"""
    print("Testing template engine...")
    
    from hasapi.templates import Template, html, TemplateResponse
    
    # Test HTML builder
    div = html.div(
        html.h1("Hello World", class_="title"),
        html.p("This is a test paragraph"),
        class_="container"
    )
    
    print(f"HTML output: {div}")
    assert "Hello World" in div
    assert "container" in div
    print("✅ HTML builder works!")
    
    # Test layout
    from hasapi.templates import default_layout
    layout = default_layout("Test App")
    wrapped = layout.wrap("<h1>Content</h1>")
    assert "Test App" in wrapped
    assert "Content" in wrapped
    print("✅ Layout system works!")
    
    print()


def test_ui_components():
    """Test UI components"""
    print("Testing UI components...")
    
    from hasapi.ui import UI, Textbox, Number, Text, Slider, Button
    
    # Test Textbox
    textbox = Textbox(label="Name", placeholder="Enter name")
    assert textbox.label == "Name"
    print("✅ Textbox works!")
    
    # Test Number
    number = Number(label="Age", value=25, minimum=0, maximum=100)
    assert number.value == 25
    print("✅ Number works!")
    
    # Test Slider
    slider = Slider(label="Temperature", value=0.7, minimum=0, maximum=1, step=0.1)
    assert slider.value == 0.7
    print("✅ Slider works!")
    
    # Test Button
    button = Button(value="Submit", variant="primary")
    assert button.value == "Submit"
    print("✅ Button works!")
    
    # Test Text output
    text = Text(label="Result")
    assert text.label == "Result"
    print("✅ Text works!")
    
    print()


def test_ui_interface():
    """Test UI interface creation"""
    print("Testing UI interface...")
    
    from hasapi.ui import UI, Textbox, Text
    
    def greet(name):
        return f"Hello, {name}!"
    
    ui = UI(
        fn=greet,
        inputs=Textbox(label="Name"),
        outputs=Text(label="Greeting"),
        title="Greeter",
        api_name="greet"
    )
    
    assert ui.title == "Greeter"
    assert ui.api_name == "greet"
    
    # Test function call
    result = ui.fn("World")
    assert result == "Hello, World!"
    print("✅ UI interface works!")
    
    # Test template rendering
    template = ui._render_template()
    assert "Greeter" in template
    print("✅ UI template rendering works!")
    
    print()


def test_app_integration():
    """Test app integration"""
    print("Testing app integration...")
    
    from hasapi import HasAPI, JSONResponse
    from hasapi.templates import Template
    
    app = HasAPI(title="Test App")
    
    @app.get("/")
    async def root(request):
        return JSONResponse({"message": "Hello"})
    
    # Check route was registered
    routes = app.router.get_routes_by_method("GET")
    assert len(routes) > 0
    print("✅ Route registration works!")
    
    # Test template engine integration
    template_engine = Template(app)
    assert template_engine.app == app
    print("✅ Template engine integration works!")
    
    print()


def main():
    """Run all tests"""
    print("Running simplified HasAPI tests...")
    print("=" * 50)
    print()
    
    test_template_engine()
    test_ui_components()
    test_ui_interface()
    test_app_integration()
    
    print("=" * 50)
    print("✅ All tests passed!")


if __name__ == "__main__":
    main()
