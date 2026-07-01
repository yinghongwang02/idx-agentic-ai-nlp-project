from typing import Any

from src.memory.base_memory import BaseMemory


class SessionMemory(BaseMemory):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()