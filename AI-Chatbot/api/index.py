# This file is the serverless function entry point for Vercel.
import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
_backend_dir = os.path.join(_parent_dir, "backend")

for p in (_parent_dir, _backend_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import app
