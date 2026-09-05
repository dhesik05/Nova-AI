# Nova AI

Your Intelligent AI Assistant powered by Groq. Conversational intelligence with streaming chat, document Q&A, and fast responses.

## Prerequisites
- Python 3.10+
- PowerShell 5.1+ (Windows 11)
- Groq API key

## Configure environment
1. Copy example env:
   
```powershell
   cd "D:\Nova AI\AI-Chatbot"
   Copy-Item ".env.example" ".env"
   
```
2. Edit `.env` and set:
   - `GROQ_API_KEY`

## Install & start (PowerShell)
```powershell
cd "D:\Nova AI\AI-Chatbot"
.\start.ps1
```

After startup, open:
- http://127.0.0.1:8000

## Verify installation
```powershell
cd "D:\Nova AI\AI-Chatbot"
python .\verify.py
```

## Endpoints
- `GET /health`
- Chat streaming:
  - `POST /api/chat/stream` (used by the frontend)
  - `POST /chat` (compat alias)

Health response includes:
- app version
- database connectivity
- Groq configuration status
- selected model

## Notes
- Speech-to-text uses Faster-Whisper (Windows-friendly).
- Speech and RAG/upload features are scaffolds (some routes currently return placeholders).

