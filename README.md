# QuickAPI - Modern Python Framework for AI-Native APIs

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.0.1-red.svg)](https://github.com/quickapi/quickapi)

**QuickAPI** is a modern Python web framework designed specifically for building AI-native APIs. Unlike traditional frameworks, QuickAPI ships with native support for LLMs, RAG systems, embeddings, and vector databases, while remaining lightweight and modular.

## 🎯 Why QuickAPI?

- **🚀 Fast** - Up to 2.92x faster than FastAPI in real-world scenarios
- **🤖 AI-Native** - Built-in LLM, RAG, and embeddings support
- **🔌 Pluggable** - Modular architecture with swappable backends
- **💾 Database-Ready** - Abstract storage layers for easy SQLite/PostgreSQL integration
- **📦 Lightweight** - Install only what you need
- **🎨 Simple** - Less boilerplate, more productivity

## �  Performance Benchmarks

QuickAPI consistently outperforms popular Python frameworks:

```
Framework Comparison (5000 requests, 50 concurrent)
┌───────────┬──────────┬──────────────────┬──────────────┐
│ Framework │ RPS      │ Avg Latency (ms) │ Success Rate │
├───────────┼──────────┼──────────────────┼──────────────┤
│ QuickAPI  │ 2,226    │ 0.45             │ 100.0%       │
│ FastAPI   │   762    │ 1.31             │ 100.0%       │
│ Flask     │ 2,040    │ 0.49             │ 100.0%       │
└───────────┴──────────┴──────────────────┴──────────────┘

🥇 QuickAPI is 2.92x faster than FastAPI
🥈 QuickAPI is 1.09x faster than Flask
```

*Benchmarks run on macOS with Python 3.13. See [benchmarks/](benchmarks/) for details.*

## 📦 Installation

```bash
# Core framework only
pip install quickapi

# With AI support (LLM, RAG, Embeddings)
pip install quickapi[ai]

# With all features
pip install quickapi[all]
```

## 🏁 Quick Start

### 1. Minimal API (Hello World)

```python
from quickapi import QuickAPI, JSONResponse

app = QuickAPI(title="My API", version="1.0.0")

@app.get("/")
async def root(request):
    return JSONResponse({"message": "Hello from QuickAPI!"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. AI Chatbot with Conversation History

```python
import os
from quickapi import QuickAPI, JSONResponse
from quickapi.ai import LLM, ConversationManager

# Initialize LLM (supports OpenAI, Claude, or custom providers)
llm = LLM(
    provider="openai",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Conversation manager with pluggable storage (in-memory, SQLite, PostgreSQL)
conversation_manager = ConversationManager()

app = QuickAPI(title="AI Chatbot")

@app.post("/chat/{conversation_id}")
async def chat(request, conversation_id: str):
    body = await request.json()
    message = body.get("message", "")
    
    # Get or create conversation
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    
    # Add user message
    conversation.add_message("user", message)
    
    # Build context with system prompt + history
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]
    messages.extend(conversation.get_context())
    
    # Get AI response
    result = await llm.chat(messages, temperature=0.7)
    
    # Save assistant response
    conversation.add_message("assistant", result["content"])
    
    return JSONResponse({
        "response": result["content"],
        "conversation_id": conversation_id
    })
```

### 3. RAG (Retrieval-Augmented Generation) System

```python
import os
from quickapi import QuickAPI, JSONResponse
from quickapi.ai import LLM, RAG, Embeddings, ConversationManager
from quickapi.ai.vectors import InMemoryVectorStore

# Initialize components
llm = LLM("openai", api_key=os.getenv("OPENAI_API_KEY"))
embeddings = Embeddings("openai", api_key=os.getenv("OPENAI_API_KEY"))
vector_store = InMemoryVectorStore(dimension=embeddings.get_dimension())

# Initialize RAG system
rag = RAG(
    embeddings=embeddings,
    llm=llm,
    vector_store=vector_store,
    similarity_threshold=0.3  # Adjust for precision/recall tradeoff
)

conversation_manager = ConversationManager()

app = QuickAPI(title="RAG Knowledge Base")

@app.post("/documents")
async def upload_document(request):
    """Upload documents to knowledge base"""
    body = await request.json()
    text = body.get("text", "")
    
    # Add document (automatically chunks, embeds, and stores)
    doc_ids = await rag.add_texts([text])
    
    return JSONResponse({"id": doc_ids[0], "status": "uploaded"})

@app.post("/chat/{conversation_id}")
async def rag_chat(request, conversation_id: str):
    """Chat with your documents"""
    body = await request.json()
    message = body.get("message", "")
    
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    conversation.add_message("user", message)
    
    # RAG answer with retrieved context
    result = await rag.answer(message, top_k=3)
    
    conversation.add_message("assistant", result["answer"])
    
    return JSONResponse({
        "answer": result["answer"],
        "sources": result["sources"],  # Retrieved documents with scores
        "conversation_id": conversation_id
    })
```

## 🤖 AI Features

### LLM Support

Unified interface for multiple LLM providers:

```python
from quickapi.ai import LLM

# OpenAI
llm = LLM("openai", api_key="sk-...")

# Claude
llm = LLM("claude", api_key="sk-ant-...")

# OpenAI-compatible (Vercel AI Gateway, Groq, etc.)
llm = LLM("openai", api_key="...", base_url="https://api.groq.com/v1")

# Chat completion
response = await llm.chat([
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
], model="gpt-4", temperature=0.7)

print(response["content"])

# Streaming
async for token in llm.stream([
    {"role": "user", "content": "Tell me a story"}
]):
    print(token, end="", flush=True)
```

### RAG (Retrieval-Augmented Generation)

Built-in RAG with automatic chunking, embedding, and retrieval:

```python
from quickapi.ai import RAG, Embeddings, LLM

# Initialize RAG
rag = RAG(
    embeddings=Embeddings("openai", api_key="..."),
    llm=LLM("openai", api_key="..."),
    top_k=5,
    similarity_threshold=0.3
)

# Add documents (automatically chunks and embeds)
await rag.add_texts([
    "QuickAPI is a modern Python framework for AI-native APIs.",
    "It provides built-in support for LLM, RAG, and embeddings."
])

# Query with automatic context retrieval
result = await rag.answer("What is QuickAPI?")

print(result["answer"])  # AI-generated answer
print(result["sources"])  # Retrieved documents with similarity scores
```

### Embeddings & Vector Search

```python
from quickapi.ai import Embeddings

# Initialize embeddings
embeddings = Embeddings("openai", api_key="...", model="text-embedding-3-small")

# Generate embeddings
embedding = await embeddings.embed("Hello, world!")
print(embedding.shape)  # (1536,)

# Batch embeddings
embeddings_batch = await embeddings.embed([
    "First document",
    "Second document"
])

# Semantic search
results = await embeddings.search(
    query="machine learning",
    documents=["AI is transforming tech", "Python is popular"],
    top_k=2
)
```

### Conversation Management

Database-ready conversation storage with pluggable backends:

```python
from quickapi.ai import ConversationManager, ChatMemory

# In-memory (default)
manager = ConversationManager()

# SQLite (future)
# from quickapi.ai.chat_memory import SQLiteChatBackend
# backend = SQLiteChatBackend("chat.db")
# manager = ConversationManager(backend=backend)

# Create conversation
conv_id = manager.create_conversation()

# Get conversation
conversation = manager.get_conversation(conv_id)

# Add messages
conversation.add_message("user", "Hello!")
conversation.add_message("assistant", "Hi there!")

# Get context for LLM
context = conversation.get_context()  # Returns last N messages

# Export/import
data = conversation.export_conversation(format="json")
conversation.load_conversation(data, format="json")
```

### Vector Stores

Pluggable vector storage backends:

```python
from quickapi.ai.vectors import InMemoryVectorStore

# In-memory vector store
vector_store = InMemoryVectorStore(dimension=1536)

# Add vectors
await vector_store.add_vectors(
    vectors=embeddings_array,
    ids=["doc1", "doc2"],
    metadata=[{"source": "file1"}, {"source": "file2"}]
)

# Search
results = await vector_store.search(
    query_vector=query_embedding,
    top_k=5
)

# Future: FAISS, Qdrant, Pinecone, etc.
```

## 🌐 WebSocket & Streaming

### WebSocket Support

```python
from quickapi import QuickAPI
from quickapi.websocket import WebSocket

app = QuickAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"Echo: {message}")
    except:
        await websocket.close()
```

### Server-Sent Events (SSE)

```python
from quickapi import QuickAPI
from quickapi.response import ServerSentEventResponse

app = QuickAPI()

@app.get("/events")
async def events(request):
    async def generate_events():
        for i in range(10):
            yield {"data": f"Event {i}", "event": "update"}
    
    return ServerSentEventResponse(generate_events())
```

## 🔧 Middleware

### CORS

```python
from quickapi.middleware import CORSMiddleware

app.middleware(CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True
))
```

### JWT Authentication

```python
from quickapi.middleware import JWTAuthMiddleware

app.middleware(JWTAuthMiddleware(
    secret_key="your-secret-key",
    algorithm="HS256",
    exclude_paths=["/health", "/docs", "/auth/login"]
))
```

### Custom Middleware

```python
from quickapi.middleware import BaseMiddleware

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, request, call_next):
        print(f"Request: {request.method} {request.path}")
        response = await call_next(request)
        print(f"Response: {response.status_code}")
        return response

app.middleware(LoggingMiddleware())
```

## 📚 Examples

Check out the [examples/](examples/) directory for complete working examples:

- **[minimal_api.py](examples/minimal_api.py)** - Basic REST API
- **[simple_chatbot.py](examples/simple_chatbot.py)** - AI chatbot with conversation history
- **[simple_rag.py](examples/simple_rag.py)** - RAG system with document upload and Q&A
- **[full_api.py](examples/full_api.py)** - Complete REST API with auth, CRUD, and docs

Run any example:
```bash
python examples/simple_chatbot.py
# Open http://localhost:8000
```

## 🔗 API Documentation

QuickAPI automatically generates OpenAPI/Swagger documentation:

- **Interactive docs**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

Add documentation to your endpoints:

```python
from quickapi import api_doc

@app.get("/users/{user_id}")
@api_doc(
    summary="Get user by ID",
    tags=["Users"],
    responses={
        "200": {"description": "User found"},
        "404": {"description": "User not found"}
    }
)
async def get_user(request, user_id: str):
    return JSONResponse({"id": user_id, "name": "John"})
```

## 🧩 Architecture

```
QuickAPI
├── Core Framework
│   ├── ASGI Server (Uvicorn)
│   ├── Router & Request Handling
│   ├── Response Types (JSON, HTML, SSE, Stream)
│   ├── WebSocket Support
│   └── OpenAPI/Swagger Generation
│
├── Middleware Layer
│   ├── CORS
│   ├── JWT Authentication
│   ├── Rate Limiting
│   └── Custom Middleware
│
├── AI Module (quickapi.ai)
│   ├── LLM
│   │   ├── OpenAI Provider
│   │   ├── Claude Provider
│   │   └── Custom Provider
│   │
│   ├── Embeddings
│   │   ├── OpenAI Embeddings
│   │   ├── Sentence Transformers
│   │   └── Custom Embeddings
│   │
│   ├── RAG
│   │   ├── Document Management
│   │   ├── Text Splitting
│   │   ├── Retrieval
│   │   └── Answer Generation
│   │
│   ├── Chat Memory
│   │   ├── In-Memory Backend
│   │   ├── SQLite Backend (future)
│   │   └── PostgreSQL Backend (future)
│   │
│   └── Vector Stores
│       ├── InMemoryVectorStore
│       ├── FAISS (future)
│       └── Qdrant (future)
│
└── CLI Tools
    ├── Project Scaffolding
    ├── Development Server
    └── Docker Generation
```

## 🛣 Roadmap

### ✅ v0.0.1 (Current - MVP)
- [x] Core ASGI framework
- [x] JSON/HTML responses
- [x] WebSocket support
- [x] LLM integration (OpenAI, Claude)
- [x] RAG with vector search
- [x] Embeddings
- [x] Conversation management
- [x] In-memory vector store
- [x] OpenAPI/Swagger docs
- [x] Middleware (CORS, JWT)

### 🚧 v0.0.5 (Next)
- [ ] CLI tool (`quickapi create`, `quickapi run`)
- [ ] SQLite chat backend
- [ ] PostgreSQL chat backend
- [ ] FAISS vector store
- [ ] Streaming RAG responses
- [ ] Model auto-loader
- [ ] Enhanced benchmarks

### 🔮 v0.1.0 (Public Beta)
- [ ] Qdrant vector store
- [ ] Redis chat backend
- [ ] Plugin system
- [ ] Web playground UI
- [ ] Production deployment guides
- [ ] Performance optimizations

### 🎯 v1.0 (Stable)
- [ ] Production-ready
- [ ] Comprehensive documentation
- [ ] Community plugins
- [ ] Enterprise features
- [ ] Multi-language support

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report bugs** - Open an issue with details
2. **Suggest features** - Share your ideas
3. **Submit PRs** - Fix bugs or add features
4. **Write docs** - Improve documentation
5. **Share examples** - Show what you've built

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

QuickAPI is licensed under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Inspired by **FastAPI**'s elegant API design
- Built on **Starlette** and **Uvicorn** for ASGI support
- AI patterns influenced by **LangChain** and **LlamaIndex**
- Performance insights from the Python async community

## 📞 Support

- **Documentation**: [Coming soon]
- **Issues**: [GitHub Issues](https://github.com/quickapi/quickapi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/quickapi/quickapi/discussions)

---

**Built with ❤️ for the AI developer community**
