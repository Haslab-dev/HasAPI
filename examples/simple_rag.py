"""
HasAPI Simple RAG with DeepSeek

Minimal RAG (Retrieval-Augmented Generation) example:
1. Upload documents
2. Store as vectors (embeddings)
3. Chat with your documents
4. AI answers based on document context

Uses HasAPI's built-in AI module for LLM and embeddings!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hasapi import HasAPI, JSONResponse
from hasapi.middleware import CORSMiddleware
from hasapi.ai import LLM, RAG, Embeddings, ConversationManager
from hasapi.ai.vectors import InMemoryVectorStore

from dotenv import load_dotenv
load_dotenv()

# Configuration
GATEWAY_URL = "https://ai-gateway.vercel.sh/v1"
GATEWAY_API_KEY = os.getenv("VERCEL_GATEWAY_API_KEY", "your-vercel-gateway-api-key-here")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek/deepseek-chat")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

# Initialize components
llm = LLM(provider="openai", api_key=GATEWAY_API_KEY, base_url=GATEWAY_URL)
embeddings = Embeddings(provider="openai", api_key=GATEWAY_API_KEY, model=EMBEDDING_MODEL, base_url=GATEWAY_URL)
vector_store = InMemoryVectorStore(dimension=embeddings.get_dimension())
rag = RAG(embeddings=embeddings, llm=llm, vector_store=vector_store, top_k=3, similarity_threshold=0.3)
conversation_manager = ConversationManager()

app = HasAPI(title="Simple RAG", version="1.0.0", debug=True)
app.middleware(CORSMiddleware(allow_origins=["*"]))


@app.post("/api/documents")
async def upload_document(request):
    """Upload a document and store it in RAG system"""
    body = await request.json()
    text = body.get("text", "")
    metadata = body.get("metadata", {})
    
    if not text:
        return JSONResponse({"error": "Text is required"}, status_code=400)
    
    try:
        doc_ids = await rag.add_texts([text], metadata=[metadata] if metadata else None)
        return JSONResponse({
            "id": doc_ids[0] if doc_ids else "unknown",
            "text": text[:100] + "..." if len(text) > 100 else text,
            "metadata": metadata
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to process document: {str(e)}"}, status_code=500)


@app.get("/api/documents")
async def list_documents(request):
    """List all documents from RAG system"""
    documents = await rag.list_documents()
    return JSONResponse({
        "documents": [{"id": doc.id, "text": doc.text[:100] + "..."} for doc in documents],
        "total": len(documents)
    })


@app.delete("/api/documents/{doc_id}")
async def delete_document(request, doc_id: str):
    """Delete a document from RAG system"""
    deleted = await rag.delete_documents([doc_id])
    if deleted:
        return JSONResponse({"message": "Document deleted"})
    return JSONResponse({"error": "Document not found"}, status_code=404)


@app.post("/api/rag/chat/{conversation_id}")
async def rag_chat(request, conversation_id: str):
    """Chat with RAG - AI answers based on document context"""
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    body = await request.json()
    message = body.get("message", "")
    
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)
    
    if len(await rag.list_documents()) == 0:
        return JSONResponse({"error": "No documents uploaded."}, status_code=400)
    
    try:
        conversation.add_message("user", message)
        result = await rag.answer(message, top_k=3)
        conversation.add_message("assistant", result["answer"])
        
        return JSONResponse({
            "conversation_id": conversation_id,
            "assistant_response": result["answer"],
            "sources": result["sources"]
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to get AI response: {str(e)}"}, status_code=500)


@app.get("/")
async def root(request):
    """Serve the RAG chatbot HTML page"""
    from hasapi.response import HTMLResponse
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>HasAPI RAG</title></head>
<body><h1>HasAPI RAG Chatbot</h1><p>Upload documents and chat with them.</p></body></html>""")


@app.get("/api/health")
async def health(request):
    """Health check endpoint"""
    docs = await rag.list_documents()
    return JSONResponse({
        "status": "healthy",
        "total_documents": len(docs),
        "chat_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL
    })


if __name__ == "__main__":
    import uvicorn
    print("Starting HasAPI Simple RAG on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
