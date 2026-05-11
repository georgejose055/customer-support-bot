from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_pipeline import load_chain, get_response
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import httpx
import asyncio
import os

load_dotenv()

app = FastAPI(title="Customer Support Bot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

chain = load_chain()

class ChatRequest(BaseModel):
    message: str

async def trigger_escalation(user_message: str, bot_answer: str, reason: str, channel: str = "web"):
    webhook_url = os.getenv("N8N_ESCALATION_WEBHOOK")
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook_url, json={
                    "user_message": user_message,
                    "bot_answer": bot_answer,
                    "reason": reason,
                    "channel": channel
                })
        except Exception as e:
            print(f"Escalation webhook failed: {e}")

# ── Chat endpoint ──────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    result = get_response(chain, req.message)
    if result["escalate"]:
        asyncio.create_task(trigger_escalation(
            user_message=req.message,
            bot_answer=result["answer"],
            reason=result.get("reason", "unknown"),
            channel="web"
        ))
    return result

# ── Twilio WhatsApp webhook ────────────────────────────────
@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, Body: str = Form(...)):
    result = get_response(chain, Body)
    if result["escalate"]:
        asyncio.create_task(trigger_escalation(
            user_message=Body,
            bot_answer=result["answer"],
            reason=result.get("reason", "unknown"),
            channel="whatsapp"
        ))
    twiml = MessagingResponse()
    reply = result["answer"]
    if result["escalate"]:
        reply += "\n\n🔔 A human agent has been notified and will reach out shortly."
    twiml.message(reply)
    return str(twiml)

# ── Health check ───────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": "llama-3.1-8b-instant"}