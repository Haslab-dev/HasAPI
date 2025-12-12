# HasAPI - Modern Python Framework for AI-Native APIs & UIs

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.0.1-red.svg)](https://github.com/hasapi/hasapi)

**HasAPI** is a modern Python web framework designed for building AI-native APIs and interactive UIs. It combines the power of FastAPI-style APIs with Gradio-like UI components, plus native support for LLMs, RAG systems, embeddings, and templates.

## 🎯 Why HasAPI?

- **🚀 Fast** - Up to 2.92x faster than FastAPI in real-world scenarios
- **🤖 AI-Native** - Built-in LLM, RAG, and embeddings support
- **🎨 UI Components** - Gradio-like interface components for rapid prototyping
- **📄 Template Engine** - File-based HTML templates with Python f-string syntax
- **🔌 Pluggable** - Modular architecture with swappable backends
- **💾 Database-Ready** - Abstract storage layers for easy SQLite/PostgreSQL integration
- **📦 Lightweight** - Install only what you need

## 📦 Installation

```bash
# Core framework only
pip install hasapi

# With AI support (LLM, RAG, Embeddings)
pip install hasapi[ai]

# With all features
pip install hasapi[all]
```

## 🏁 Quick Start

### Minimal API

```python
from hasapi import HasAPI, JSONResponse

app = HasAPI(title="My API", version="1.0.0")

@app.get("/")
async def root(request):
    return JSONResponse({"message": "Hello from HasAPI!"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### AI Chatbot

```python
import os
from hasapi import HasAPI, JSONResponse
from hasapi.ai import LLM, ConversationManager

llm = LLM(provider="openai", api_key=os.getenv("OPENAI_API_KEY"))
conversation_manager = ConversationManager()

app = HasAPI(title="AI Chatbot")

@app.post("/chat/{conversation_id}")
async def chat(request, conversation_id: str):
    body = await request.json()
    message = body.get("message", "")
    
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    conversation.add_message("user", message)
    
    messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
    messages.extend(conversation.get_context())
    
    result = await llm.chat(messages, temperature=0.7)
    conversation.add_message("assistant", result["content"])
    
    return JSONResponse({"response": result["content"]})
```

### RAG System

```python
import os
from hasapi import HasAPI, JSONResponse
from hasapi.ai import LLM, RAG, Embeddings
from hasapi.ai.vectors import InMemoryVectorStore

llm = LLM("openai", api_key=os.getenv("OPENAI_API_KEY"))
embeddings = Embeddings("openai", api_key=os.getenv("OPENAI_API_KEY"))
vector_store = InMemoryVectorStore(dimension=embeddings.get_dimension())
rag = RAG(embeddings=embeddings, llm=llm, vector_store=vector_store)

app = HasAPI(title="RAG Knowledge Base")

@app.post("/documents")
async def upload_document(request):
    body = await request.json()
    doc_ids = await rag.add_texts([body.get("text", "")])
    return JSONResponse({"id": doc_ids[0]})

@app.post("/chat")
async def rag_chat(request):
    body = await request.json()
    result = await rag.answer(body.get("message", ""), top_k=3)
    return JSONResponse({"answer": result["answer"], "sources": result["sources"]})
```

## 🎨 UI Components

```python
from hasapi import HasAPI
from hasapi.ui import UI, Textbox, Text
from hasapi.templates import default_layout, TemplateResponse

def analyze_sentiment(text):
    positive = ["good", "great", "awesome", "love", "happy"]
    negative = ["bad", "terrible", "hate", "sad", "awful"]
    text_lower = text.lower()
    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    if pos > neg: return "😊 Positive"
    elif neg > pos: return "😢 Negative"
    return "😐 Neutral"

app = HasAPI(title="Sentiment Analysis")

sentiment_ui = UI(
    fn=analyze_sentiment,
    inputs=Textbox(label="Enter text"),
    outputs=Text(label="Sentiment"),
    title="📝 Sentiment Analysis"
)

@app.get("/")
async def sentiment_page(request):
    layout = default_layout(sentiment_ui.title)
    return TemplateResponse(
        template_string=layout.wrap(sentiment_ui._render_template()),
        title=sentiment_ui.title,
        custom_js=sentiment_ui._get_javascript()
    )

sentiment_ui._setup_api_endpoint(app)
```

## 🤖 AI Features

### LLM Support

```python
from hasapi.ai import LLM

llm = LLM("openai", api_key="sk-...")
# or: LLM("claude", api_key="sk-ant-...")
# or: LLM("openai", api_key="...", base_url="https://api.groq.com/v1")

response = await llm.chat([
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Hello!"}
])
```

### RAG

```python
from hasapi.ai import RAG, Embeddings, LLM

rag = RAG(
    embeddings=Embeddings("openai", api_key="..."),
    llm=LLM("openai", api_key="...")
)

await rag.add_texts(["Document 1", "Document 2"])
result = await rag.answer("What is in the documents?")
```

## 🔧 Middleware

```python
from hasapi.middleware import CORSMiddleware, JWTAuthMiddleware

app.middleware(CORSMiddleware(allow_origins=["*"]))
app.middleware(JWTAuthMiddleware(secret_key="your-secret"))
```

## 📚 Examples

- `examples/minimal_api.py` - Basic REST API
- `examples/simple_chatbot.py` - AI chatbot
- `examples/simple_rag.py` - RAG system
- `examples/full_api.py` - Complete REST API with auth
- `examples/simple_demo.py` - UI components demo

## 🔗 API Documentation

HasAPI automatically generates OpenAPI/Swagger docs at `/docs`.

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

**Built with ❤️ for the AI developer community**
