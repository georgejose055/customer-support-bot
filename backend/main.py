from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load RAG pipeline only if vectorstore exists
rag_chain = None
try:
    from rag_pipeline import get_rag_chain
    rag_chain = get_rag_chain()
    print("✅ RAG pipeline loaded successfully")
except Exception as e:
    print(f"⚠️ RAG pipeline not loaded: {e}")
    print("Running in fallback mode")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    escalated: bool = False

N8N_WEBHOOK = os.getenv("N8N_ESCALATION_WEBHOOK", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

async def escalate_to_human(message: str, session_id: str):
    if not N8N_WEBHOOK:
        print("No webhook configured, skipping escalation")
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(N8N_WEBHOOK, json={
                "message": message,
                "session_id": session_id,
                "timestamp": str(__import__("datetime").datetime.now())
            }, timeout=5.0)
    except Exception as e:
        print(f"Escalation failed: {e}")

def should_escalate(response: str) -> bool:
    escalation_triggers = [
        "i don't know", "i'm not sure", "cannot help",
        "speak to a human", "contact support", "not available",
        "unclear", "i cannot", "i am unable"
    ]
    return any(trigger in response.lower() for trigger in escalation_triggers)

@app.get("/")
def root():
    return {"status": "ok", "message": "Customer Support Bot API is running 🚀"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "rag_loaded": rag_chain is not None,
        "groq_configured": bool(GROQ_API_KEY)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if rag_chain is None:
        # Fallback: use Groq directly without RAG
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful customer support assistant."},
                    {"role": "user", "content": request.message}
                ],
                max_tokens=512
            )
            response_text = completion.choices[0].message.content
        except Exception as e:
            response_text = f"I'm having trouble connecting right now. Please try again later."
            print(f"Groq fallback error: {e}")
    else:
        try:
            response_text = rag_chain.invoke(request.message)
        except Exception as e:
            response_text = "I'm unable to process that right now."
            print(f"RAG error: {e}")

    escalated = should_escalate(response_text)
    if escalated:
        await escalate_to_human(request.message, request.session_id)

    return ChatResponse(response=response_text, escalated=escalated)