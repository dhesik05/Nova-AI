import asyncio
from typing import AsyncIterator, List, Optional

from groq import Groq

from .config import settings


# ── Valid Groq model IDs ──────────────────────────────────────────────────────
AVAILABLE_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

# Display-friendly labels shown in the model selector dropdown
MODEL_LABELS = {
    "llama-3.1-8b-instant":    "Llama 3.1 8B   (fast ⚡)",
    "llama-3.3-70b-versatile": "Llama 3.3 70B  (smart)",
    "llama3-70b-8192":         "Llama 3 70B",
    "llama3-8b-8192":          "Llama 3 8B",
    "gemma2-9b-it":            "Gemma 2 9B",
    "mixtral-8x7b-32768":      "Mixtral 8×7B   (32k ctx)",
}

DEFAULT_MODEL = "llama-3.1-8b-instant"  # Fast 8B as default for low latency


def _client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


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
    Uses an asyncio.Queue to bridge the sync Groq iterator with async code,
    avoiding repeated executor calls that can deadlock on slow generators.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _SENTINEL = object()

    def _producer():
        """Run in threadpool: consume Groq stream, push deltas to queue."""
        try:
            client = _client()
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
            )
            for event in stream:
                try:
                    delta = event.choices[0].delta.content
                except Exception:
                    delta = None
                if delta:
                    # Put into queue from thread; use thread-safe call
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
        # Ensure threadpool task is awaited even on abort
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
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",   # Use the fast 8B for titling
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
