"""
QuickAPI Simple Chatbot with DeepSeek

Simple chatbot with in-memory conversation history.
No RAG, no complex dependencies - just pure chat!
"""

import os
from typing import List, Dict
from quickapi import QuickAPI, JSONResponse
from quickapi.middleware import CORSMiddleware
from quickapi.ai import LLM, ConversationManager

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
app = QuickAPI(title="Simple Chatbot", version="1.0.0", debug=True)
app.middleware(CORSMiddleware(allow_origins=["*"]))


@app.post("/api/chat/{conversation_id}")
async def chat(request, conversation_id: str):
    """Send a message and get AI response"""
    # Get or create conversation
    conversation = conversation_manager.get_or_create_conversation(conversation_id)
    
    # Get message from request
    body = await request.json()
    message = body.get("message", "")
    
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)
    
    # Add user message to history
    conversation.add_message("user", message)
    
    # Build messages for API (system + history)
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Be concise and friendly."}
    ]
    messages.extend(conversation.get_context())
    
    try:
        # Get AI response using QuickAPI LLM
        result = await llm.chat(messages, model=MODEL, temperature=0.7)
        response = result["content"]
        
        # Add assistant response to history
        conversation.add_message("assistant", response)
        
        return JSONResponse({
            "conversation_id": conversation_id,
            "user_message": message,
            "assistant_response": response,
            "message_count": len(conversation.get_messages())
        })
    
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get AI response: {str(e)}"},
            status_code=500
        )


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
    else:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)


@app.get("/api/conversations")
async def list_conversations(request):
    """List all conversations"""
    summaries = conversation_manager.get_conversation_summaries()
    
    return JSONResponse({
        "conversations": [
            {
                "conversation_id": conv_id,
                "message_count": summary["total_messages"],
                "user_messages": summary["user_messages"],
                "assistant_messages": summary["assistant_messages"]
            }
            for conv_id, summary in summaries.items()
        ],
        "total": len(summaries)
    })


@app.get("/")
async def root(request):
    """Serve the chatbot HTML page"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>QuickAPI Chatbot</title>
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
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
            height: 85vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { font-size: 14px; opacity: 0.9; }
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
            transition: border-color 0.3s;
        }
        #messageInput:focus {
            border-color: #667eea;
        }
        #sendButton {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 24px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        #sendButton:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        #sendButton:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            padding: 8px;
            font-size: 12px;
            color: #666;
        }
        .loading {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #667eea;
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        .empty-state h2 { font-size: 18px; margin-bottom: 8px; }
        .empty-state p { font-size: 14px; }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 QuickAPI Chatbot</h1>
            <p>Powered by Vercel AI Gateway</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="empty-state">
                <h2>👋 Welcome!</h2>
                <p>Start a conversation by typing a message below</p>
            </div>
        </div>
        
        <div class="input-area">
            <div class="status" id="status"></div>
            <div class="input-group">
                <input 
                    type="text" 
                    id="messageInput" 
                    placeholder="Type your message..." 
                    autocomplete="off"
                />
                <button id="sendButton">Send</button>
            </div>
        </div>
    </div>
    
    <script>
        // Generate a unique conversation ID for this session
        const conversationId = 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        let isProcessing = false;
        
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const status = document.getElementById('status');
        
        // Add message to chat
        function addMessage(text, sender) {
            // Remove empty state if it exists
            const emptyState = chatMessages.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.textContent = text;
            
            messageDiv.appendChild(bubbleDiv);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Show error message
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Show loading indicator
        function showLoading(show) {
            if (show) {
                status.innerHTML = '<span class="loading"></span> AI is thinking...';
            } else {
                status.innerHTML = '';
            }
        }
        
        // Send message
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message || isProcessing) return;
            
            // Disable input
            isProcessing = true;
            sendButton.disabled = true;
            messageInput.disabled = true;
            
            // Add user message
            addMessage(message, 'user');
            messageInput.value = '';
            
            // Show loading
            showLoading(true);
            
            try {
                // Send to API
                const response = await fetch(`/api/chat/${conversationId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to get response');
                }
                
                // Add assistant response
                addMessage(data.assistant_response, 'assistant');
                
            } catch (error) {
                console.error('Error:', error);
                showError('Error: ' + error.message);
            } finally {
                // Re-enable input
                isProcessing = false;
                sendButton.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
                showLoading(false);
            }
        }
        
        // Event listeners
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Focus input on load
        messageInput.focus();
        
        console.log('Conversation ID:', conversationId);
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
    return JSONResponse({
        "status": "healthy",
        "total_conversations": len(conversation_manager.list_conversations()),
        "model": MODEL,
        "gateway": "Vercel AI Gateway",
        "gateway_url": GATEWAY_URL,
        "api_configured": is_configured
    })


if __name__ == "__main__":
    import uvicorn
    print("🤖 Starting QuickAPI Simple Chatbot")
    print("🌐 Open your browser: http://localhost:8000")
    print(f"🧠 Model: {MODEL}")
    print(f"🌐 Gateway: Vercel AI Gateway")
    print()
    if GATEWAY_API_KEY == "your-vercel-gateway-api-key-here":
        print("⚠️  WARNING: Please set your Vercel AI Gateway API key in the code!")
        print("   Edit GATEWAY_API_KEY variable at the top of simple_chatbot.py")
        print("   Get key from: https://vercel.com/docs/ai-gateway")
    else:
        print("✅ API key configured")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
