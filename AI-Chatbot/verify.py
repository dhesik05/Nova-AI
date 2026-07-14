import importlib
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime

from typing import Literal

from dotenv import load_dotenv


Status = Literal["PASS", "WARN", "FAIL"]


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""


def _is_venv(p: str) -> bool:
    # Heuristic: venv folder typically contains "pyvenv.cfg"
    return os.path.isfile(os.path.join(p, "pyvenv.cfg"))


def _print_and_count(checks: list[CheckResult]) -> int:
    print(f"Verification run: {datetime.now().isoformat(timespec='seconds')}")
    totals = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for c in checks:
        totals[c.status] += 1
        symbol = "[OK]" if c.status == "PASS" else ("[WARN]" if c.status == "WARN" else "[FAIL]")
        print(f"[{c.status}] {symbol} {c.name}" + (f" - {c.detail}" if c.detail else ""))

    print(
        "Summary: "
        f"Total Checks={len(checks)}, "
        f"Passed={totals['PASS']}, "
        f"Warnings={totals['WARN']}, "
        f"Failed={totals['FAIL']}"
    )
    return 1 if totals["FAIL"] > 0 else 0


def main() -> int:
    checks: list[CheckResult] = []

    def add(name: str, status: Status, detail: str = ""):
        checks.append(CheckResult(name=name, status=status, detail=detail))

    project_root = os.path.dirname(os.path.abspath(__file__))

    # Load .env explicitly so verification reflects real runtime config.
    env_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=env_path, override=False)

    # 1) Python version (critical)
    add(
        "Python version >= 3.10",
        "PASS" if sys.version_info >= (3, 10) else "FAIL",
        f"found={platform.python_version()}",
    )

    # 2) virtual environment (recommended-> FAIL by policy per user request)
    venv_dir = os.path.join(project_root, ".venv")
    active_prefix = getattr(sys, "base_prefix", "")
    real_prefix = getattr(sys, "prefix", "")
    using_venv = _is_venv(venv_dir) or (real_prefix and active_prefix and real_prefix != active_prefix)
    add(
        "Virtual environment present",
        "PASS" if using_venv else "FAIL",
        f"venv_dir={venv_dir} exists={os.path.isdir(venv_dir)}",
    )

    # 3) required packages import (critical)
    required_imports = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("groq", "groq"),
        ("faster_whisper", "faster_whisper"),
    ]
    for mod, label in required_imports:
        try:
            importlib.import_module(mod)
            add(f"Dependency import: {label}", "PASS")
        except Exception as e:
            add(f"Dependency import: {label}", "FAIL", str(e))

    # 4) .env exists (critical)
    env_exists = os.path.isfile(env_path)
    add(
        ".env exists",
        "PASS" if env_exists else "FAIL",
        f"path={env_path}",
    )

    # 5) Load config (critical - config validates on import)
    try:
        importlib.import_module("backend.app.config")
        add("Config validation (GROQ_API_KEY required)", "PASS")
    except Exception as e:
        add("Config validation (GROQ_API_KEY required)", "FAIL", str(e))

    # 6) GROQ_API_KEY present (critical)
    groq_key = os.environ.get("GROQ_API_KEY") or ""
    add(
        "GROQ_API_KEY in environment",
        "PASS" if groq_key else "FAIL",
        "loaded_from_env_file=True" if groq_key else (
            "Missing. Set AI-Chatbot/.env or environment variables. "
            "Create it from AI-Chatbot/.env.example."
        ),
    )

    # 7) Groq authentication succeeds (critical - best-effort model list)
    try:
        from groq import Groq

        from backend.app.config import settings

        client = Groq(api_key=settings.groq_api_key)
        client.models.list()  # may raise if invalid/unauthorized
        add("Groq API authentication succeeds", "PASS")
    except Exception as e:
        add("Groq API authentication succeeds", "FAIL", str(e))

    # 8) FastAPI application import (critical)
    try:
        importlib.import_module("backend.app.main")
        add("FastAPI app import", "PASS")
    except Exception as e:
        add("FastAPI app import", "FAIL", str(e))

    # 9) Database connectivity (critical)
    try:
        db_module = importlib.import_module("backend.app.database")
        engine = db_module.engine
        conn = engine.connect()
        conn.close()
        add("SQLite DB connectivity", "PASS")
    except Exception as e:
        add("SQLite DB connectivity", "FAIL", str(e))

    # 10) upload / vector_store directories (critical, but attempt create)
    backend_dir = os.path.join(project_root, "backend")
    upload_dir = os.path.join(backend_dir, "uploads")
    vector_dir = os.path.join(backend_dir, "vector_store")
    try:
        os.makedirs(upload_dir, exist_ok=True)
        add("Upload directory exists", "PASS", f"path={upload_dir}")
    except Exception as e:
        add("Upload directory exists", "FAIL", f"path={upload_dir} - {e}")
    try:
        os.makedirs(vector_dir, exist_ok=True)
        add("Vector-store directory exists", "PASS", f"path={vector_dir}")
    except Exception as e:
        add("Vector-store directory exists", "FAIL", f"path={vector_dir} - {e}")

    # 11) Vector-store initialization succeeds (WARN - rag.py is scaffold-only)
    try:
        importlib.import_module("backend.app.rag")
        add("Vector-store initialization succeeds", "WARN", "RAG is currently scaffold-only (no vector init).")
    except Exception as e:
        add("Vector-store initialization succeeds", "FAIL", str(e))

    # 12) Routes smoke check (critical)
    try:
        from backend.app.main import create_app

        app = create_app()
        paths = {r.path for r in app.router.routes}
        add("GET /health exists", "PASS" if "/health" in paths else "FAIL", f"has={('/health' in paths)}")
        add("/chat exists (alias)", "PASS" if "/chat" in paths else "FAIL", f"has={('/chat' in paths)}")
        add(
            "POST /api/chat/stream exists",
            "PASS" if "/api/chat/stream" in paths else "FAIL",
            f"has={('/api/chat/stream' in paths)}",
        )
    except Exception as e:
        add("FastAPI route smoke check", "FAIL", str(e))

    return _print_and_count(checks)


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    raise SystemExit(main())
