# This file is the serverless function entry point for Vercel when deployed from root.
import os
import sys

_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_chatbot_dir = os.path.join(_root_dir, "AI-Chatbot")
_backend_dir = os.path.join(_chatbot_dir, "backend")

for p in (_chatbot_dir, _backend_dir, _root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import app
