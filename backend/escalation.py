import requests
import os
from dotenv import load_dotenv

load_dotenv()

def trigger_escalation(user_message: str, bot_answer: str, reason: str, channel: str = "web"):
    webhook_url = os.getenv("N8N_ESCALATION_WEBHOOK")
    if not webhook_url:
        print("⚠️ No n8n webhook URL set, skipping escalation trigger.")
        return

    payload = {
        "user_message": user_message,
        "bot_answer": bot_answer,
        "reason": reason,
        "channel": channel
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        print(f"✅ Escalation triggered: {response.status_code}")
    except Exception as e:
        print(f"❌ Escalation webhook failed: {e}")