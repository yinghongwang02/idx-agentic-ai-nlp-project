from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    """
    Abstract interface for memory implementations.

    Concrete memory classes decide how data is stored,
    updated, retrieved, and cleared.
    """

    @abstractmethod
    def update(self, values: dict[str, Any]) -> None:
        """Update memory with new non-empty values."""
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Return one value from memory."""
        raise NotImplementedError

    @abstractmethod
    def merge(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Merge the current memory with new values.

        New non-empty values take precedence over remembered values.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored values."""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Return a copy of the current memory state."""
        raise NotImplementedError