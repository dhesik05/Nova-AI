import asyncio
import time
import logging
from typing import AsyncIterator, List, Dict, Optional, Tuple

from groq import Groq

from .config import settings

logger = logging.getLogger(__name__)

# ── Fallback model IDs if API query is unavailable ────────────────────────────
DEFAULT_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "groq/compound",
    "groq/compound-mini",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# Display-friendly labels shown in the model selector dropdown
MODEL_LABELS = {
    "openai/gpt-oss-120b":     "GPT-OSS 120B (Smart & Powerful)",
    "openai/gpt-oss-20b":      "GPT-OSS 20B  (Ultra Fast ⚡)",
    "qwen/qwen3.8-27b":        "Qwen 3.8 27B (High Quality)",
    "qwen/qwen3.6-27b":        "Qwen 3.6 27B (Fast)",
    "groq/compound":           "Groq Compound",
    "groq/compound-mini":      "Groq Compound Mini",
    "llama-3.3-70b-versatile": "Llama 3.3 70B (Versatile)",
    "llama-3.1-8b-instant":    "Llama 3.1 8B (Fast)",
    "llama3-70b-8192":         "Llama 3 70B",
    "llama3-8b-8192":          "Llama 3 8B",
    "gemma2-9b-it":            "Gemma 2 9B",
    "mixtral-8x7b-32768":      "Mixtral 8×7B",
}

DEFAULT_MODEL = "openai/gpt-oss-120b"
FAST_TITLE_MODEL = "openai/gpt-oss-20b"

# Cached model list
_cached_models: List[str] = []
_cache_timestamp: float = 0.0
_CACHE_TTL = 300.0  # 5 minutes


def _client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def get_available_models() -> Tuple[List[str], Dict[str, str], str]:
    """
    Fetch the list of valid chat models supported by the current Groq API key.
    Caches results for 5 minutes.
    """
    global _cached_models, _cache_timestamp
    now = time.time()
    if _cached_models and (now - _cache_timestamp < _CACHE_TTL):
        models = _cached_models
    else:
        try:
            client = _client()
            all_models = client.models.list().data
            # Filter out non-chat models (audio, moderation guards)
            chat_models = [
                m.id for m in all_models
                if not m.id.startswith("whisper")
                and "guard" not in m.id.lower()
                and "orpheus" not in m.id.lower()
            ]
            if chat_models:
                # Prioritize primary flagship models if present
                preferred_order = [
                    "openai/gpt-oss-120b",
                    "openai/gpt-oss-20b",
                    "qwen/qwen3.8-27b",
                    "qwen/qwen3.6-27b",
                    "groq/compound",
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                ]
                sorted_models = [m for m in preferred_order if m in chat_models]
                for m in chat_models:
                    if m not in sorted_models:
                        sorted_models.append(m)
                _cached_models = sorted_models
                _cache_timestamp = now
                models = _cached_models
            else:
                models = DEFAULT_MODELS
        except Exception as e:
            logger.warning("Failed to query Groq model list, using defaults: %s", e)
            models = DEFAULT_MODELS

    # Build dynamic labels
    labels = {}
    for m in models:
        labels[m] = MODEL_LABELS.get(m, m.split("/")[-1].replace("-", " ").title())

    default_m = models[0] if models else DEFAULT_MODEL
    return models, labels, default_m


# ── Streaming chat completion ─────────────────────────────────────────────────
async def stream_chat(
    *,
    messages: List[dict],
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    """
    Yield text delta strings from a Groq streaming completion.
    Uses an asyncio.Queue to bridge the sync Groq iterator with async code.
    If the requested model is not found, automatically falls back to the default available model.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _SENTINEL = object()

    def _producer():
        """Run in threadpool: consume Groq stream, push deltas to queue."""
        active_model = model
        try:
            client = _client()
            try:
                stream = client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stream=True,
                )
            except Exception as first_err:
                # If model is not found on this key, attempt fallback to default model
                err_str = str(first_err).lower()
                if "model_not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                    logger.warning("Model '%s' failed (%s). Retrying with '%s'", active_model, first_err, DEFAULT_MODEL)
                    active_model = DEFAULT_MODEL
                    stream = client.chat.completions.create(
                        model=active_model,
                        messages=messages,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                else:
                    raise first_err

            for event in stream:
                try:
                    delta = event.choices[0].delta.content
                except Exception:
                    delta = None
                if delta:
                    asyncio.run_coroutine_threadsafe(queue.put(delta), loop).result()
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(_SENTINEL), loop).result()

    # Start the blocking producer in a threadpool
    future = loop.run_in_executor(None, _producer)

    try:
        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        try:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            pass


# ── Auto-title generation ─────────────────────────────────────────────────────
async def auto_title(first_user_message: str) -> str:
    """
    Generate a concise 4–6 word title for a conversation from the first user message.
    Returns a plain string (no quotes, no punctuation at end).
    Falls back gracefully if the API call fails.
    """
    if not first_user_message or not (settings.groq_api_key or "").strip():
        return _fallback_title(first_user_message)

    prompt = (
        "Generate a concise 4-6 word title for a chat conversation that starts with "
        "the following user message. Return ONLY the title — no quotes, no punctuation "
        "at the end, no explanation.\n\n"
        f"User message: {first_user_message[:400]}"
    )

    try:
        loop = asyncio.get_running_loop()
        client = _client()

        def _call():
            title_model = FAST_TITLE_MODEL
            try:
                resp = client.chat.completions.create(
                    model=title_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=20,
                    stream=False,
                )
            except Exception:
                resp = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=20,
                    stream=False,
                )
            return resp.choices[0].message.content.strip().strip('"').strip("'")

        title = await loop.run_in_executor(None, _call)
        return title or _fallback_title(first_user_message)
    except Exception:
        return _fallback_title(first_user_message)


def _fallback_title(text: str) -> str:
    """Truncate the first user message to produce a readable title."""
    clean = (text or "New chat").strip().replace("\n", " ")
    return clean[:50] + ("…" if len(clean) > 50 else "")

