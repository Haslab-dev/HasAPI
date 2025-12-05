"""
QuickAPI Simple RAG with DeepSeek

Minimal RAG (Retrieval-Augmented Generation) example:
1. Upload documents
2. Store as vectors (embeddings)
3. Chat with your documents
4. AI answers based on document context

Uses QuickAPI's built-in AI module for LLM and embeddings!
"""

import os
import json
from typing import List, Dict
from quickapi import QuickAPI, JSONResponse
from quickapi.middleware import CORSMiddleware
from quickapi.ai import LLM, RAG, Embeddings, ConversationManager
from quickapi.ai.vectors import InMemoryVectorStore

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# CONFIGURATION - Loaded from .env file
# ============================================================================
# Vercel AI Gateway
GATEWAY_URL = "https://ai-gateway.vercel.sh/v1"
GATEWAY_API_KEY = os.getenv("VERCEL_GATEWAY_API_KEY", "your-vercel-gateway-api-key-here")

# Models (via Vercel Gateway)
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek/deepseek-chat")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
# ============================================================================

# Initialize LLM with Vercel AI Gateway
llm = LLM(
    provider="openai",
    api_key=GATEWAY_API_KEY,
    base_url=GATEWAY_URL
)

# Initialize Embeddings with Vercel AI Gateway
embeddings = Embeddings(
    provider="openai",
    api_key=GATEWAY_API_KEY,
    model=EMBEDDING_MODEL,
    base_url=GATEWAY_URL
)

# Initialize vector store for document embeddings (in-memory, can be swapped with persistent storage)
vector_store = InMemoryVectorStore(dimension=embeddings.get_dimension())

# Initialize RAG system (combines LLM, Embeddings, and VectorStore)
rag = RAG(
    embeddings=embeddings,
    llm=llm,
    vector_store=vector_store,
    top_k=3,
    similarity_threshold=0.3  # Lower threshold for better recall
)

# Initialize conversation manager for chat history
conversation_manager = ConversationManager()

# Create the app
app = QuickAPI(title="Simple RAG", version="1.0.0", debug=True)
app.middleware(CORSMiddleware(allow_origins=["*"]))


# ============================================================================
# Helper Functions
# ============================================================================
# (RAG class handles most of the heavy lifting now!)


# ============================================================================
# Document Management Endpoints
# ============================================================================

@app.post("/api/documents")
async def upload_document(request):
    """Upload a document and store it in RAG system"""
    body = await request.json()
    text = body.get("text", "")
    metadata = body.get("metadata", {})
    
    if not text:
        return JSONResponse({"error": "Text is required"}, status_code=400)
    
    try:
        # Add document to RAG system (handles embedding + vector storage automatically)
        # add_texts expects a list, so we pass [text] and [metadata]
        doc_ids = await rag.add_texts([text], metadata=[metadata] if metadata else None)
        
        return JSONResponse({
            "id": doc_ids[0] if doc_ids else "unknown",
            "text": text[:100] + "..." if len(text) > 100 else text,
            "metadata": metadata,
            "embedding_dimension": embeddings.get_dimension()
        })
    
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to process document: {str(e)}"},
            status_code=500
        )


@app.get("/api/documents")
async def list_documents(request):
    """List all documents from RAG system"""
    documents = await rag.list_documents()
    
    return JSONResponse({
        "documents": [
            {
                "id": doc.id,
                "text": doc.text[:100] + "..." if len(doc.text) > 100 else doc.text,
                "metadata": doc.metadata
            }
            for doc in documents
        ],
        "total": len(documents)
    })


@app.delete("/api/documents/{doc_id}")
async def delete_document(request, doc_id: str):
    """Delete a document from RAG system"""
    deleted = await rag.delete_documents([doc_id])
    
    if deleted:
        return JSONResponse({"message": "Document deleted"})
    else:
        return JSONResponse({"error": "Document not found"}, status_code=404)


@app.delete("/api/documents")
async def clear_documents(request):
    """Clear all documents from RAG system"""
    # Clear vector store
    await vector_store.clear()
    # Clear RAG documents dict
    rag.documents.clear()
    return JSONResponse({"message": "All documents cleared"})


# ============================================================================
# RAG Chat Endpoints
# ============================================================================

@app.post("/api/rag/search")
async def search(request):
    """Search documents by query using RAG system"""
    body = await request.json()
    query = body.get("query", "")
    top_k = body.get("top_k", 3)
    
    if not query:
        return JSONResponse({"error": "Query is required"}, status_code=400)
    
    try:
        # Search using RAG system's query method
        result = await rag.query(query, top_k=top_k)
        
        return JSONResponse({
            "query": query,
            "results": [
                {
                    "id": doc_data["document"]["id"],
                    "text": doc_data["document"]["text"],
                    "metadata": doc_data["document"]["metadata"],
                    "similarity": doc_data["score"]
                }
                for doc_data in result["retrieved_documents"]
            ],
            "total": result["total_retrieved"]
        })
    
    except Exception as e:
        return JSONResponse(
            {"error": f"Search failed: {str(e)}"},
            status_code=500
        )


@app.post("/api/rag/chat/{conversation_id}")
async def rag_chat(request, conversation_id: str):
    """Chat with RAG - AI answers based on document context"""
    # Get or create conversation
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    
    # Get message from request
    body = await request.json()
    message = body.get("message", "")
    
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)
    
    if len(await rag.list_documents()) == 0:
        return JSONResponse(
            {"error": "No documents uploaded. Please upload documents first."},
            status_code=400
        )
    
    try:
        # Add user message to history
        conversation.add_message("user", message)
        
        # Use RAG system to answer the question
        result = await rag.answer(message, top_k=3)
        
        # Add assistant response to history
        conversation.add_message("assistant", result["answer"])
        
        return JSONResponse({
            "conversation_id": conversation_id,
            "user_message": message,
            "assistant_response": result["answer"],
            "relevant_documents": [
                {
                    "id": source["id"],
                    "similarity": source["score"],
                    "text": doc_data["document"]["text"][:200] + "..." 
                           if len(doc_data["document"]["text"]) > 200 
                           else doc_data["document"]["text"]
                }
                for doc_data, source in zip(result["retrieved_documents"], result["sources"])
            ],
            "message_count": len(conversation.get_messages())
        })
    
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get AI response: {str(e)}"},
            status_code=500
        )


# ============================================================================
# Web UI
# ============================================================================

@app.get("/")
async def root(request):
    """Serve the RAG chatbot HTML page"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>QuickAPI RAG Chatbot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
            height: 85vh;
        }
        .panel {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 20px; margin-bottom: 5px; }
        .header p { font-size: 12px; opacity: 0.9; }
        .content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            min-height: 100px;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            resize: vertical;
            margin-bottom: 10px;
        }
        button {
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .doc-list {
            margin-top: 20px;
        }
        .doc-item {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .doc-item .doc-id {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 4px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 16px;
            display: flex;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user { justify-content: flex-end; }
        .message.assistant { justify-content: flex-start; }
        .message-bubble {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }
        .message.user .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .message.assistant .message-bubble {
            background: white;
            color: #333;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .sources {
            font-size: 11px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(0,0,0,0.1);
            color: #666;
        }
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 24px;
            font-size: 14px;
            outline: none;
        }
        #messageInput:focus { border-color: #667eea; }
        .status {
            text-align: center;
            padding: 8px;
            font-size: 12px;
            color: #666;
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 14px;
        }
        .success {
            background: #efe;
            color: #3c3;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Panel: Document Upload -->
        <div class="panel">
            <div class="header">
                <h1>📚 Documents</h1>
                <p>Upload documents to chat with</p>
            </div>
            <div class="content">
                <div class="upload-area">
                    <h3>Upload Document</h3>
                    <textarea id="docText" placeholder="Paste your document text here..."></textarea>
                    <button onclick="uploadDocument()">Upload</button>
                    <button onclick="clearDocuments()" style="background: #dc3545; margin-left: 10px;">Clear All</button>
                </div>
                <div id="uploadStatus"></div>
                <div class="doc-list">
                    <h4>Uploaded Documents (<span id="docCount">0</span>)</h4>
                    <div id="docList"></div>
                </div>
            </div>
        </div>
        
        <!-- Right Panel: Chat -->
        <div class="panel">
            <div class="header">
                <h1>🤖 RAG Chat</h1>
                <p>Ask questions about your documents</p>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="empty-state">
                    <h2>👋 Welcome to RAG Chat!</h2>
                    <p>Upload documents on the left, then ask questions about them</p>
                </div>
            </div>
            <div class="input-area">
                <div class="status" id="status"></div>
                <div class="input-group">
                    <input 
                        type="text" 
                        id="messageInput" 
                        placeholder="Ask a question about your documents..." 
                        autocomplete="off"
                    />
                    <button id="sendButton" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const conversationId = 'conv_' + Date.now();
        let isProcessing = false;
        
        // Upload document
        async function uploadDocument() {
            const text = document.getElementById('docText').value.trim();
            if (!text) {
                showStatus('Please enter document text', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/documents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('docText').value = '';
                    showStatus('Document uploaded successfully!', 'success');
                    loadDocuments();
                } else {
                    showStatus('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }
        
        // Load documents
        async function loadDocuments() {
            try {
                const response = await fetch('/api/documents');
                const data = await response.json();
                
                document.getElementById('docCount').textContent = data.total;
                
                const docList = document.getElementById('docList');
                docList.innerHTML = '';
                
                data.documents.forEach(doc => {
                    const div = document.createElement('div');
                    div.className = 'doc-item';
                    div.innerHTML = `
                        <div class="doc-id">${doc.id}</div>
                        <div>${doc.text}</div>
                    `;
                    docList.appendChild(div);
                });
            } catch (error) {
                console.error('Error loading documents:', error);
            }
        }
        
        // Clear documents
        async function clearDocuments() {
            if (!confirm('Clear all documents?')) return;
            
            try {
                await fetch('/api/documents', { method: 'DELETE' });
                showStatus('All documents cleared', 'success');
                loadDocuments();
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }
        
        // Send message
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message || isProcessing) return;
            
            isProcessing = true;
            document.getElementById('sendButton').disabled = true;
            input.disabled = true;
            
            addMessage(message, 'user');
            input.value = '';
            showLoading(true);
            
            try {
                const response = await fetch(`/api/rag/chat/${conversationId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    addMessage(data.assistant_response, 'assistant', data.relevant_documents);
                } else {
                    addError(data.error);
                }
            } catch (error) {
                addError('Error: ' + error.message);
            } finally {
                isProcessing = false;
                document.getElementById('sendButton').disabled = false;
                input.disabled = false;
                input.focus();
                showLoading(false);
            }
        }
        
        // Add message to chat
        function addMessage(text, sender, sources = null) {
            const emptyState = document.querySelector('.empty-state');
            if (emptyState) emptyState.remove();
            
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.textContent = text;
            
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.innerHTML = '📄 Sources: ' + sources.map(s => 
                    `${s.id} (${(s.similarity * 100).toFixed(0)}%)`
                ).join(', ');
                bubbleDiv.appendChild(sourcesDiv);
            }
            
            messageDiv.appendChild(bubbleDiv);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function addError(message) {
            const chatMessages = document.getElementById('chatMessages');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('uploadStatus');
            statusDiv.className = type;
            statusDiv.textContent = message;
            setTimeout(() => statusDiv.textContent = '', 3000);
        }
        
        function showLoading(show) {
            document.getElementById('status').textContent = show ? '🤔 AI is thinking...' : '';
        }
        
        // Event listeners
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Load documents on start
        loadDocuments();
    </script>
</body>
</html>
    """
    
    from quickapi.response import HTMLResponse
    return HTMLResponse(html_content)


@app.get("/api/health")
async def health(request):
    """Health check endpoint"""
    is_configured = GATEWAY_API_KEY and GATEWAY_API_KEY != "your-vercel-gateway-api-key-here"
    docs = await rag.list_documents()
    
    return JSONResponse({
        "status": "healthy",
        "total_documents": len(docs),
        "total_conversations": len(conversation_manager.list_conversations()),
        "vector_store_size": vector_store.size(),
        "embedding_dimension": embeddings.get_dimension(),
        "chat_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "gateway": "Vercel AI Gateway",
        "api_configured": is_configured,
        "modules_used": ["LLM", "RAG", "Embeddings", "ConversationManager", "InMemoryVectorStore"]
    })


if __name__ == "__main__":
    import uvicorn
    print("🤖 Starting QuickAPI Simple RAG")
    print("🌐 Open your browser: http://localhost:8000")
    print(f"🧠 Chat Model: {CHAT_MODEL}")
    print(f"📊 Embedding: {EMBEDDING_MODEL}")
    print(f"🌐 Gateway: Vercel AI Gateway")
    print()
    if GATEWAY_API_KEY == "your-vercel-gateway-api-key-here":
        print("⚠️  WARNING: Please set your Vercel AI Gateway API key in the code!")
        print("   Edit GATEWAY_API_KEY variable at the top of simple_rag.py")
        print("   Get key from: https://vercel.com/docs/ai-gateway")
    else:
        print("✅ API key configured")
    print()
    print("📚 How to use:")
    print("   1. Upload documents (left panel)")
    print("   2. Ask questions about them (right panel)")
    print("   3. AI answers based on document context")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
