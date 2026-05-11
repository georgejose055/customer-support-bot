from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
get_response_fn = None

try:
    from rag_pipeline import load_chain, get_response
    rag_chain = load_chain()
    get_response_fn = get_response
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


@app.get("/")
def root():
    return {"message": "Customer Support Bot API is running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "rag_loaded": rag_chain is not None,
        "groq_configured": True,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.lower()

    # Escalation check
    escalation_keywords = ["human", "agent", "speak to human", "real person", "supervisor"]
    if any(keyword in message for keyword in escalation_keywords):
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
            print(f"RAG error: {e}")

    # Fallback: use Groq directly
    try:
        from groq import Groq
        import os

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
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
        print(f"Groq fallback error: {e}")
        return ChatResponse(
            response="I'm having trouble connecting right now. Please try again in a moment.",
            escalated=False,
        )