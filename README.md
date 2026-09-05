# ✨ Nova AI — Intelligent Conversational Assistant & Document RAG Platform

<p align="center">
  <img src="AI-Chatbot/frontend/assets/logo.svg" alt="Nova AI Logo" width="90" height="90" />
</p>

<p align="center">
  <strong>Fast, private, and powerful AI assistant built with FastAPI, Groq LLM inference, and a modern ChatGPT-inspired UI.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Groq-LPU%20Inference-F55036.svg?logo=groq&logoColor=white" alt="Groq LPU" />
  <img src="https://img.shields.io/badge/Vercel-Serverless%20Ready-black.svg?logo=vercel&logoColor=white" alt="Vercel Ready" />
  <img src="https://img.shields.io/badge/Theme-Purple%20%26%20White-7C3AED.svg" alt="Purple & White Theme" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

---

## 🌟 Overview

**Nova AI** is a full-stack, enterprise-grade AI chatbot platform designed for speed, beauty, and simplicity. Powered by ultra-low-latency **Groq LPU inference**, Nova AI delivers real-time token streaming, document Q&A via an embedded RAG pipeline, multimodal image analysis, voice recognition, and conversation sharing.

### 🎨 Design Philosophy
* **Royal Purple & Crisp White**: Harmonious, modern color palette with glassmorphism, glowing micro-animations, and full dark/light mode toggle.
* **ChatGPT Mobile App Experience**: Responsive layout featuring a sticky topbar with a model pill selector, collapsible sliding drawer for conversation history, and a floating pill composer with safe-area insets.
* **Direct Name Login**: Zero friction access — users simply enter their name to start chatting with instant profile creation.

---

## 🚀 Key Features

* ⚡ **Ultra-Fast LLM Streaming**: Real-time NDJSON / SSE streaming using Groq's high-speed inference engine (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`).
* 📄 **Zero-Bloat RAG (Document Q&A)**: Upload PDFs to automatically extract text, generate structured segments, and perform relevance ranking with automatic source citations (`[Document: resume.pdf, Page 1]`).
* 🖼️ **Image & Multimodal Attachment**: Attach images (PNG, JPG, WEBP, GIF) with base64 rendering and AI vision analysis.
* 🎙️ **Speech-to-Text & Text-to-Speech**: In-browser voice recording and neural audio synthesis.
* 🔒 **Secure Direct Authentication**: Instant name-based login generating stateless JWTs, with session persistence in `localStorage`.
* 🔗 **Shareable Public Links**: Create public links to share conversations with syntax highlighting and read-only views.
* 📥 **Export Options**: Export any conversation transcript to formatted **PDF** or **TXT** files.
* 🌐 **Serverless & Local Ready**: 100% compatible with both Vercel Serverless Functions and local desktop/server hosting.

---

## 🏗️ Architecture & Project Structure

```text
Nova-AI/
├── vercel.json                 # Vercel deployment configuration (Root)
├── requirements.txt            # Root build dependencies
├── api/
│   └── index.py                # Root serverless function entrypoint
└── AI-Chatbot/
    ├── .env.example            # Environment template
    ├── start.ps1               # One-click Windows PowerShell launcher
    ├── start.bat               # Windows Batch launcher
    ├── verify.py               # Diagnostics & system verification script
    ├── requirements.txt        # Full application dependencies
    ├── vercel.json             # Subfolder Vercel deployment configuration
    ├── api/
    │   └── index.py            # Subfolder serverless entrypoint
    ├── backend/
    │   ├── app/
    │   │   ├── main.py         # FastAPI application factory & routes
    │   │   ├── config.py       # Pydantic environment configuration
    │   │   ├── database.py     # SQLAlchemy engine & SQLite setup
    │   │   ├── models.py       # ORM Models (User, Conversation, Message, DocumentChunk)
    │   │   ├── schemas.py      # Pydantic request/response schemas
    │   │   ├── ai.py           # Groq client, dynamic model discovery & streaming
    │   │   ├── auth.py         # JWT tokens & Name login endpoint
    │   │   ├── rag.py          # PyMuPDF parser, chunking & relevance search
    │   │   ├── speech.py       # Speech-to-text & transcription utilities
    │   │   └── routes/         # Modular route handlers (chat, upload, history, export, share)
    │   └── tests/              # Pytest test suite (15/15 unit tests)
    └── frontend/
        ├── index.html          # Main SPA interface
        ├── share.html          # Public conversation viewer
        ├── assets/             # SVG Logos, Favicons, and Vector Graphics
        ├── css/
        │   ├── variables.css   # CSS design tokens & purple theme variables
        │   ├── style.css       # Core design system & component styles
        │   └── responsive.css  # ChatGPT-inspired mobile layout styles
        └── js/
            ├── auth.js         # Name Login & JWT token manager
            └── app.js          # Core application logic & UI streaming
```

---

## ⚡ Quickstart Guide

### Prerequisites
* **Python**: `3.10` or newer
* **Groq API Key**: Obtain a free API key at [console.groq.com](https://console.groq.com)

### 1. Clone the Repository
```bash
git clone https://github.com/dhesik05/Nova-AI.git
cd Nova-AI/AI-Chatbot
```

### 2. Configure Environment Variables
Create a `.env` file in `AI-Chatbot/`:
```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
DEFAULT_MODEL=openai/gpt-oss-120b
JWT_SECRET_KEY=generate_a_random_32_character_secret_key
CORS_ORIGINS=*
```

### 3. Launch the Application

#### On Windows (PowerShell):
```powershell
.\start.ps1
```

#### On Linux / macOS / Manual:
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **`http://localhost:8000`** in your browser.

---

## 🧪 Testing & Verification

Run the built-in system verification tool to validate your environment and API connectivity:
```bash
python verify.py
```

Run the automated test suite:
```bash
pytest backend/tests
```

---

## ☁️ Deployment Guide

### Deploying to Vercel

1. Push your repository to GitHub (`https://github.com/dhesik05/Nova-AI`).
2. Log into [Vercel](https://vercel.com) and click **"Add New Project"**.
3. Import the **Nova-AI** repository.
4. Under **Environment Variables**, add:
   * `GROQ_API_KEY`: Your Groq API key.
   * `JWT_SECRET_KEY`: A random secret string (e.g. `nova_secret_key_2026`).
5. Click **Deploy**. Both root `./` and subfolder `AI-Chatbot/` configurations are supported automatically.

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate with username and receive a JWT access token |
| `GET` | `/api/auth/me` | Retrieve current user profile and session info |
| `GET` | `/api/chat/models` | List available Groq AI models and active defaults |
| `POST` | `/api/chat/stream` | Stream chat completion responses (NDJSON / SSE) |
| `POST` | `/api/upload/pdf` | Upload and index PDF document for RAG Q&A |
| `POST` | `/api/upload/image` | Upload image for preview and multimodal analysis |
| `GET` | `/api/history/conversations` | List conversation history for current user |
| `DELETE` | `/api/history/conversations/{id}` | Delete a conversation and associated message records |
| `POST` | `/api/share` | Generate a public shareable URL for a conversation |
| `GET` | `/api/export/pdf/{id}` | Export a conversation transcript as formatted PDF |
| `GET` | `/api/export/txt/{id}` | Export a conversation transcript as plain text |
| `GET` | `/health` | Healthcheck endpoint reporting DB and Groq status |

---

## 🛠️ Technology Stack

* **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [Groq Python SDK](https://github.com/groq/groq-python), [PyMuPDF](https://pymupdf.readthedocs.io/), [Edge-TTS](https://github.com/rany2/edge-tts), [PyJWT](https://pyjwt.readthedocs.io/).
* **Frontend**: HTML5, Vanilla CSS3 (Custom Design System, Glassmorphism, Responsive Grid), JavaScript (ES Modules).
* **Libraries**: [Marked.js](https://marked.js.org/) (Markdown rendering), [Highlight.js](https://highlightjs.org/) (Syntax highlighting), [DOMPurify](https://github.com/cure53/DOMPurify) (XSS sanitization).
* **Database**: SQLite (local / persistent) & In-Memory for ephemeral serverless execution.

---

## 📄 License

This project is licensed under the **MIT License**. Feel free to use, modify, and distribute it for personal or commercial projects.
