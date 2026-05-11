from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load RAG pipeline
rag_chain = None
get_response_fn = None

try:
    from rag_pipeline import load_chain, get_response
    rag_chain = load_chain()
    get_response_fn = get_response
    print("✅ RAG pipeline loaded successfully")
except Exception as e:
    print(f"⚠️ RAG pipeline not loaded: {type(e).__name__}: {e}")
    print("Running in fallback mode")


def trigger_n8n_escalation(user_message: str, session_id: str):
    """Trigger N8n webhook on escalation."""
    try:
        webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        if not webhook_url:
            print("⚠️ N8N_WEBHOOK_URL not set — skipping notification")
            return

        payload = {
            "session_id": session_id,
            "user_message": user_message,
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        with httpx.Client(timeout=5.0) as client:
            response = client.post(webhook_url, json=payload)
            print(f"✅ N8n webhook triggered: status={response.status_code}")

    except Exception as e:
        print(f"❌ N8n webhook failed: {type(e).__name__}: {e}")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    escalated: bool = False


@app.get("/")
def root():
    return {"message": "Customer Support Bot API is running"}


@app.get("/health")
def health():
    groq_key = os.environ.get("GROQ_API_KEY")
    return {
        "status": "healthy",
        "rag_loaded": rag_chain is not None,
        "groq_configured": bool(groq_key and len(groq_key) > 10),
        "n8n_configured": bool(os.environ.get("N8N_WEBHOOK_URL")),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.lower()

    # Escalation check
    escalation_keywords = ["human", "agent", "speak to human", "real person", "supervisor"]
    if any(keyword in message for keyword in escalation_keywords):
        trigger_n8n_escalation(request.message, request.session_id)
        return ChatResponse(
            response="I'll connect you with a human agent right away. Please hold on.",
            escalated=True,
        )

    # Use RAG pipeline if available
    if rag_chain and get_response_fn:
        try:
            response_text = get_response_fn(rag_chain, request.message)
            return ChatResponse(response=response_text, escalated=False)
        except Exception as e:
            print(f"RAG error: {type(e).__name__}: {e}")

    # Fallback: use Groq directly
    try:
        from groq import Groq

        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        client = Groq(api_key=groq_key)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful customer support assistant. Be concise, friendly, and professional.",
                },
                {"role": "user", "content": request.message},
            ],
            max_tokens=512,
        )
        response_text = completion.choices[0].message.content
        return ChatResponse(response=response_text, escalated=False)

    except Exception as e:
        print(f"Groq fallback error: {type(e).__name__}: {e}")
        return ChatResponse(
            response="I'm having trouble connecting right now. Please try again in a moment.",
            escalated=False,
        )