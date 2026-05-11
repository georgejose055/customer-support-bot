# 🤖 AI Customer Support Bot

An intelligent customer support chatbot built with RAG (Retrieval-Augmented Generation), LangChain, FastAPI, and Next.js — with automatic human escalation via n8n.

## ✨ Features
- 💬 RAG-powered responses trained on client documents
- 🔔 Auto-escalation when bot is unsure
- 📊 Google Sheets logging of all escalations
- 📧 Gmail email alerts on escalation
- 📱 WhatsApp support via Twilio
- ⚡ Built with Next.js + FastAPI + FAISS + Groq LLaMA

## 🏗️ Architecture

User → Next.js UI → FastAPI → LangChain RAG → Groq LLaMA
↓
FAISS Vectorstore
↓
Escalation → n8n → Google Sheets + Gmail


## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python ingest.py
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### n8n Workflow
```bash
n8n start
# Import n8n-workflow/escalation_workflow.json
```

## 🔑 Environment Variables
Create `backend/.env`:
GROQ_API_KEY=your_groq_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
N8N_ESCALATION_WEBHOOK=http://localhost:5678/webhook/escalate


## 🛠️ Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| AI/RAG | LangChain, FAISS, Sentence Transformers |
| LLM | Groq LLaMA 3.1 8B |
| Automation | n8n |
| Messaging | Twilio WhatsApp |