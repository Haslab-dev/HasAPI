"""
Simple HasAPI Demo

Demonstrates the simplified template engine and UI components.
"""

import sys
import os

# Add parent directory to path so we can import hasapi
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hasapi import HasAPI
from hasapi.templates import Template, html, TemplateResponse, default_layout
from hasapi.ui import UI, Textbox, Slider, Text, Button, Number


# ============================================================================
# BUSINESS LOGIC
# ============================================================================

def analyze_sentiment(text):
    """Simple sentiment analysis"""
    positive_words = ["good", "great", "awesome", "love", "happy", "excellent"]
    negative_words = ["bad", "terrible", "hate", "sad", "awful"]
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "😊 Positive"
    elif negative_count > positive_count:
        return "😢 Negative"
    else:
        return "😐 Neutral"


def calculate_power(base, exponent):
    """Calculate base to the power of exponent"""
    try:
        result = base ** exponent
        return f"{base}^{exponent} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# TEMPLATE UI EXAMPLE
# ============================================================================

async def template_demo(request):
    """Simple template UI demo using SimpleTemplate engine"""
    return {
        "title": "📄 Simple Template Demo",
        "message": "Hello from the HasAPI simplified template engine!",
        "item1": "Feature-rich template engine",
        "item2": "Server-side rendering", 
        "item3": "Dynamic content generation",
        "template_name": "demo.html",
        "var_count": "7 variables"
    }


async def advanced_template_demo(request):
    """Advanced template demo using SimpleTemplate engine"""
    import datetime
    return {
        "title": "🎨 Advanced Template Demo",
        "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": "HasAPI User",
        "user_email": "user@example.com",
        "template_vars": 12,
        "feature1": "Real-time generation",
        "feature2": "Nested object support",
        "feature3": "Live data binding",
        "status": "Active",
        "version": "v1.0",
        "mode": "Production"
    }


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def create_app():
    """Create the demo application"""
    app = HasAPI(title="Simple HasAPI Demo")
    
    # Initialize template engine
    template_engine = Template(app)
    
    # Register template routes using HTML template files
    template_engine.route("/template", "examples/templates/demo.html")(template_demo)
    template_engine.route("/template/advanced", "examples/templates/advanced.html")(advanced_template_demo)
    

    
    # Register static files
    template_engine.static("/static", "static")
    
    # ============================================================================
    # SIMPLE UI INTERFACES
    # ============================================================================
    
    # Sentiment analysis interface
    sentiment_ui = UI(
        fn=analyze_sentiment,
        inputs=Textbox(label="Enter text", placeholder="Type something here..."),
        outputs=Text(label="Sentiment"),
        title="📝 Sentiment Analysis",
        description="Analyze the sentiment of text.",
        api_name="sentiment"
    )
    
    # Power calculator interface
    power_ui = UI(
        fn=calculate_power,
        inputs=[
            Number(label="Base", value=2),
            Number(label="Exponent", value=3)
        ],
        outputs=Text(label="Result"),
        title="🔢 Power Calculator",
        description="Calculate base to the power of exponent.",
        api_name="power"
    )
    
    # ============================================================================
    # ROUTES FOR UI INTERFACES
    # ============================================================================
    
    @app.get("/")
    async def index(request):
        """Main index page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple HasAPI Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-900 mb-4">🚀 Simple HasAPI Demo</h1>
            <p class="text-xl text-gray-600 mb-8">Minimal template engine and UI components</p>
            <div class="flex justify-center gap-4 flex-wrap">
                <a href="/template" class="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors">
                    📄 Template Demo
                </a>
                <a href="/template/advanced" class="px-6 py-3 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium transition-colors">
                    🎨 Advanced Template
                </a>
                <a href="/sentiment" class="px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors">
                    💭 Sentiment Analysis
                </a>
                <a href="/power" class="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors">
                    🔢 Power Calculator
                </a>
            </div>
        </div>
    </div>
</body>
</html>
        """
        from hasapi.response import HTMLResponse
        return HTMLResponse(html_content)
    
    @app.get("/sentiment")
    async def sentiment_page(request):
        """Sentiment analysis UI page"""
        layout = default_layout(sentiment_ui.title)
        template = sentiment_ui._render_template()
        return TemplateResponse(
            template_string=layout.wrap(template),
            title=sentiment_ui.title,
            custom_js=sentiment_ui._get_javascript()
        )
    
    @app.get("/power")
    async def power_page(request):
        """Power calculator UI page"""
        layout = default_layout(power_ui.title)
        template = power_ui._render_template()
        return TemplateResponse(
            template_string=layout.wrap(template),
            title=power_ui.title,
            custom_js=power_ui._get_javascript()
        )
    
    # Setup API endpoints for UI interfaces
    sentiment_ui._setup_api_endpoint(app)
    power_ui._setup_api_endpoint(app)
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    print("🚀 Simple HasAPI Demo")
    print("=" * 50)
    print("📄 Template UI:")
    print("   GET  /template")
    print("   GET  /template/advanced")
    print("")
    print("🧩 Simple UI:")
    print("   GET  /sentiment")
    print("   GET  /power")
    print("")
    print("🌐 Open: http://127.0.0.1:8000")
    print("=" * 50)
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
