from copy import deepcopy
from typing import Any

from src.memory.base_memory import BaseMemory


class SessionMemory(BaseMemory):
    """
    In-memory storage for the current property-search session.

    The memory stores structured buyer preferences collected across
    multiple user turns, such as city, budget, bedrooms, property type,
    and requested amenities.

    This implementation lasts only for the current Python process.
    It does not provide long-term persistence.
    """

    ALLOWED_FIELDS = {
        "city",
        "state",
        "zip_code",
        "min_price",
        "max_price",
        "min_bedrooms",
        "min_bathrooms",
        "min_sqft",
        "max_sqft",
        "property_type",
        "keywords",
        "limit",
    }

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def update(self, values: dict[str, Any]) -> None:
        """
        Save newly provided search preferences.

        None values and empty strings are ignored so that an incomplete
        follow-up query does not erase previously remembered preferences.
        """
        for key, value in values.items():
            if key not in self.ALLOWED_FIELDS:
                continue

            if not self._is_meaningful(value):
                continue

            if key == "keywords" and isinstance(value, list):
                existing_keywords = self._data.get("keywords", [])

                self._data["keywords"] = list(
                    dict.fromkeys([*existing_keywords, *value])
                )
            else:
                self._data[key] = deepcopy(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Return one remembered value."""
        return deepcopy(self._data.get(key, default))

    def merge(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Combine remembered preferences with newly parsed values.

        New scalar values override remembered values.
        New keywords are combined with remembered keywords.
        This method does not mutate memory.
        """
        merged = self.to_dict()

        for key, value in values.items():
            if key not in self.ALLOWED_FIELDS:
                continue

            if not self._is_meaningful(value):
                continue

            if key == "keywords" and isinstance(value, list):
                existing_keywords = merged.get("keywords", [])

                merged["keywords"] = list(
                    dict.fromkeys([*existing_keywords, *value])
                )
            else:
                merged[key] = deepcopy(value)

        return merged

    def clear(self) -> None:
        """Clear all preferences for the current search session."""
        self._data.clear()

    def to_dict(self) -> dict[str, Any]:
        """Return a defensive copy of the memory snapshot."""
        return deepcopy(self._data)

    def is_empty(self) -> bool:
        """Return True when the session has no remembered preferences."""
        return not self._data

    def has(self, key: str) -> bool:
        """Return True when a field currently exists in memory."""
        return key in self._data

    @staticmethod
    def _is_meaningful(value: Any) -> bool:
        """
        Determine whether a value should be stored.

        Numeric zero and False remain valid values. Empty strings and
        empty collections are treated as missing.
        """
        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)

        return True