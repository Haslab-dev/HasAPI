"""
HasAPI Simple Chatbot with DeepSeek

Simple chatbot with in-memory conversation history.
No RAG, no complex dependencies - just pure chat!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict
from hasapi import HasAPI, JSONResponse
from hasapi.middleware import CORSMiddleware
from hasapi.ai import LLM, ConversationManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# CONFIGURATION - Loaded from .env file
# ============================================================================
# Vercel AI Gateway
GATEWAY_URL = "https://ai-gateway.vercel.sh/v1"
GATEWAY_API_KEY = os.getenv("VERCEL_GATEWAY_API_KEY", "your-vercel-gateway-api-key-here")

# Model (via Vercel Gateway)
MODEL = os.getenv("CHAT_MODEL", "deepseek/deepseek-chat")
# ============================================================================

# Initialize LLM with Vercel AI Gateway
llm = LLM(
    provider="openai",
    api_key=GATEWAY_API_KEY,
    base_url=GATEWAY_URL
)

# Initialize conversation manager (in-memory by default, can be swapped with SQLite later)
conversation_manager = ConversationManager()

# Create the app
app = HasAPI(title="Simple Chatbot", version="1.0.0", debug=True)
app.middleware(CORSMiddleware(allow_origins=["*"]))


@app.post("/api/chat/{conversation_id}")
async def chat(request, conversation_id: str):
    """Send a message and get AI response"""
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    body = await request.json()
    message = body.get("message", "")
    
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)
    
    conversation.add_message("user", message)
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Be concise and friendly."}
    ]
    messages.extend(conversation.get_context())
    
    try:
        result = await llm.chat(messages, model=MODEL, temperature=0.7)
        response = result["content"]
        conversation.add_message("assistant", response)
        
        return JSONResponse({
            "conversation_id": conversation_id,
            "user_message": message,
            "assistant_response": response,
            "message_count": len(conversation.get_messages())
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to get AI response: {str(e)}"}, status_code=500)


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(request, conversation_id: str):
    """Get conversation history"""
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    
    messages = conversation.get_messages()
    return JSONResponse({
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "messages": [msg.to_dict() for msg in messages]
    })


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(request, conversation_id: str):
    """Delete a conversation"""
    deleted = conversation_manager.delete_conversation(conversation_id)
    if deleted:
        return JSONResponse({"message": "Conversation deleted"})
    return JSONResponse({"error": "Conversation not found"}, status_code=404)


@app.get("/api/conversations")
async def list_conversations(request):
    """List all conversations"""
    summaries = conversation_manager.get_conversation_summaries()
    return JSONResponse({
        "conversations": [
            {"conversation_id": conv_id, "message_count": summary["total_messages"]}
            for conv_id, summary in summaries.items()
        ],
        "total": len(summaries)
    })


@app.get("/")
async def root(request):
    """Serve the chatbot HTML page"""
    from hasapi.response import HTMLResponse
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>HasAPI Chatbot</title></head>
<body><h1>HasAPI Chatbot</h1><p>Use the API endpoints to chat.</p></body></html>""")


@app.get("/api/health")
async def health(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "model": MODEL})


if __name__ == "__main__":
    import uvicorn
    print("Starting HasAPI Simple Chatbot on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
