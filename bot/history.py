from collections import defaultdict, deque

MAX_MESSAGES = 50


class ConversationHistory:
    """In-memory conversation history keyed by user ID.

    Supports both Telegram user IDs (int) and web user UUIDs (str).
    Stores the last MAX_MESSAGES exchanges (user + assistant) per user.
    Images are not stored in history to avoid memory bloat.
    """

    def __init__(self, max_messages: int = MAX_MESSAGES) -> None:
        self._max = max_messages
        self._store: dict[int | str, deque[dict]] = defaultdict(lambda: deque(maxlen=max_messages))

    def get(self, user_id: int | str) -> list[dict]:
        return list(self._store[user_id])

    def add_user(self, user_id: int | str, content: str) -> None:
        self._store[user_id].append({"role": "user", "content": content})

    def add_assistant(self, user_id: int | str, content: str) -> None:
        self._store[user_id].append({"role": "assistant", "content": content})

    def clear(self, user_id: int | str) -> None:
        self._store[user_id].clear()
