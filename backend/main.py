from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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


def send_escalation_email(user_message: str, session_id: str):
    """Send email alert when a user requests human escalation."""
    try:
        gmail_user = os.environ.get("GMAIL_USER")
        gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
        alert_email = os.environ.get("ALERT_EMAIL")

        if not all([gmail_user, gmail_password, alert_email]):
            print("⚠️ Email env vars not set — skipping email notification")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🚨 Customer Support Escalation Request"
        msg["From"] = gmail_user
        msg["To"] = alert_email

        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d9534f;">🚨 Escalation Alert</h2>
            <p>A customer has requested to speak with a human agent.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                <tr>
                    <td style="padding: 8px; font-weight: bold; background: #f5f5f5;">Session ID</td>
                    <td style="padding: 8px;">{session_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold; background: #f5f5f5;">User Message</td>
                    <td style="padding: 8px;">{user_message}</td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #888;">Please follow up with the customer as soon as possible.</p>
        </body></html>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, alert_email, msg.as_string())

        print(f"✅ Escalation email sent to {alert_email}")

    except Exception as e:
        print(f"❌ Failed to send escalation email: {type(e).__name__}: {e}")


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
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.lower()

    # Escalation check
    escalation_keywords = ["human", "agent", "speak to human", "real person", "supervisor"]
    if any(keyword in message for keyword in escalation_keywords):
        # Send email alert (non-blocking — won't crash if it fails)
        send_escalation_email(request.message, request.session_id)
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