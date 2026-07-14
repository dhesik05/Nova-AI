from typing import List


# ── Token budget ──────────────────────────────────────────────────────────────
# Conservative estimate: 1 token ≈ 4 characters of English text.
# We keep the total context well under the model's limit.
_CHARS_PER_TOKEN      = 4
_DEFAULT_TOKEN_BUDGET = 6_000   # tokens reserved for history
_MIN_TURNS_KEPT       = 3       # always keep at least the last N user+assistant pairs


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _estimate_messages_tokens(messages: List[dict]) -> int:
    return sum(_estimate_tokens(m.get("content") or "") for m in messages)


def truncate_history(
    history: List[dict],
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
    min_turns: int = _MIN_TURNS_KEPT,
) -> List[dict]:
    """
    Trim conversation history to stay within *token_budget*.

    Strategy:
    - Always keep the last *min_turns* user+assistant message pairs
      (i.e., the last min_turns*2 messages), regardless of budget.
    - Walk backwards through older messages and include them while
      the running token count stays under budget.
    - Returns messages in chronological order.

    Args:
        history:       List of {"role": ..., "content": ...} dicts (oldest first).
                       Should NOT include the system message.
        token_budget:  Max tokens to spend on history.
        min_turns:     Minimum number of recent turn-pairs to always include.

    Returns:
        Filtered list of messages, oldest first.
    """
    if not history:
        return []

    # Mandatory recent messages (last min_turns * 2, clamped to len)
    mandatory_count = min(min_turns * 2, len(history))
    mandatory       = history[-mandatory_count:]
    older           = history[:-mandatory_count]

    mandatory_tokens = _estimate_messages_tokens(mandatory)
    remaining_budget = token_budget - mandatory_tokens

    # Greedily add older messages (most recent first) within budget
    included_older: List[dict] = []
    for msg in reversed(older):
        t = _estimate_tokens(msg.get("content") or "")
        if t <= remaining_budget:
            included_older.append(msg)
            remaining_budget -= t
        else:
            break   # once we exceed budget, stop (keep history contiguous)

    return list(reversed(included_older)) + mandatory


def conversation_to_messages(
    system_prompt: str,
    history: List[dict],
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
) -> List[dict]:
    """
    Build the full messages list for the Groq API.

    1. Truncates history to stay within token_budget.
    2. Prepends the system prompt if provided.
    3. Returns messages in the order expected by the API.
    """
    trimmed = truncate_history(history, token_budget=token_budget)
    messages: List[dict] = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.extend(trimmed)
    return messages
