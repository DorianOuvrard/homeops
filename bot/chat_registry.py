class ChatRegistry:
    """Stores Telegram chat ids that interacted with the bot during runtime."""

    def __init__(self) -> None:
        self._chat_ids: set[int] = set()

    def add(self, chat_id: int) -> None:
        self._chat_ids.add(chat_id)

    def all(self) -> list[int]:
        return sorted(self._chat_ids)
