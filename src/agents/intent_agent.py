import re

from src.memory.session_memory import SessionMemory
from src.schemas.intent_schema import PropertyIntent


class IntentAgent:
    def __init__(self, memory: SessionMemory | None = None) -> None:
        """
        Create an intent parser with optional session memory.

        When memory is provided, incomplete follow-up queries inherit
        previously remembered property-search preferences.
        """
        self.memory = memory

    CITY_CANDIDATES = [
        "Irvine",
        "Newport Beach",
        "Pasadena",
        "Los Angeles",
        "San Diego",
        "Santa Monica",
    ]

    PROPERTY_TYPE_MAP = {
        # Condo
        "condo": "Condominium",
        "condos": "Condominium",
        "condominium": "Condominium",

        # Townhouse
        "townhouse": "Townhouse",
        "townhouses": "Townhouse",
        "townhome": "Townhouse",
        "townhomes": "Townhouse",

        # Single Family
        "single family": "SingleFamilyResidence",
        "single-family": "SingleFamilyResidence",
        "single family home": "SingleFamilyResidence",
        "single family homes": "SingleFamilyResidence",
        "house": "SingleFamilyResidence",
        "houses": "SingleFamilyResidence",
        "home": "SingleFamilyResidence",
        "homes": "SingleFamilyResidence",

        # Manufactured
        "manufactured": "ManufacturedOnLand",
        "manufactured home": "ManufacturedOnLand",
        "mobile home": "ManufacturedOnLand",

        # Duplex
        "duplex": "Duplex",
    }

    KEYWORD_CANDIDATES = [
        "pool",
        "spa",
        "garage",
        "parking",
        "backyard",
        "yard",
        "patio",
        "balcony",
        "fireplace",
        "view",
        "views",
        "ocean view",
        "city view",
        "mountain view",
        "beach",
        "waterfront",
        "downtown",
        "shopping",
        "parks",
        "school", 
        "schools",
        "school district",
        "luxury",
        "modern",
        "remodeled",
        "renovated",
        "updated",
        "open floor plan",
        "hardwood",
        "kitchen island",
        "walk-in closet",
        "solar",
        "adu",
        "guest house",
        "gated",
        "corner lot",
        "cul-de-sac",
        "single story",
    ]


    def run(self, query: str) -> PropertyIntent:
        """
        Parse the current user query and optionally merge it with
        preferences remembered from previous turns.
        """
        current_intent = self._parse_current_query(query)

        if self.memory is None:
            return current_intent

        current_values = current_intent.model_dump()
        merged_values = self.memory.merge(current_values)

        merged_intent = PropertyIntent(**merged_values)

        # Store only values explicitly parsed from the current turn.
        # SessionMemory ignores None and empty collections.
        self.memory.update(current_values)

        return merged_intent
    
    def _parse_current_query(self, query: str) -> PropertyIntent:
        """
        Parse only the preferences explicitly mentioned in the current
        query without using session memory.
        """
        query_lower = query.lower()
        preferences = self._parse_preferences(query_lower)

        return PropertyIntent(
            city=self._parse_city(query_lower),
            max_price=self._parse_max_price(query_lower),
            min_bedrooms=self._parse_min_bedrooms(query_lower),
            min_bathrooms=self._parse_min_bathrooms(query_lower),
            property_type=self._parse_property_type(query_lower),
            keywords=self._parse_keywords(
                query_lower=query_lower,
                preferences=preferences,
            ),
            preferences=preferences,
        )

    def _parse_city(self, query_lower: str) -> str | None:
        for city in self.CITY_CANDIDATES:
            if city.lower() in query_lower:
                return city
        return None

    def _parse_max_price(self, query_lower: str) -> int | None:
        patterns = [
            r"(?:under|below|less than|max|up to)\s*\$?([\d,.]+)\s*(k|m|million)?",
            r"\$?([\d,.]+)\s*(k|m|million)\s*(?:budget|max)?",
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if not match:
                continue

            value = float(match.group(1).replace(",", ""))
            suffix = match.group(2)

            if suffix == "k":
                value *= 1_000
            elif suffix in {"m", "million"}:
                value *= 1_000_000

            return int(value)

        return None

    def _parse_min_bedrooms(self, query_lower: str) -> int | None:
        match = re.search(
            r"(\d+)\s*[- ]?\s*(bed|beds|bedroom|bedrooms)",
            query_lower,
        )
        return int(match.group(1)) if match else None

    def _parse_min_bathrooms(self, query_lower: str) -> float | None:
        match = re.search(
            r"(\d+(?:\.5)?)\s*[- ]?\s*(bath|baths|bathroom|bathrooms)",
            query_lower,
        )
        return float(match.group(1)) if match else None

    def _parse_property_type(self, query_lower: str) -> str | None:
        for phrase, normalized_type in self.PROPERTY_TYPE_MAP.items():
            if phrase in query_lower:
                return normalized_type
        return None
    
    def _parse_preferences(
        self,
        query_lower: str,
    ) -> list[str]:
        preference_markers = [
            "preferably",
            "prefer",
            "would like",
            "nice to have",
            "ideally",
        ]

        preference_start = None

        for marker in preference_markers:
            marker_index = query_lower.find(marker)

            if marker_index != -1:
                preference_start = marker_index
                break

        if preference_start is None:
            return []

        preference_text = query_lower[
            preference_start:
        ]

        preferences = []

        for keyword in self.KEYWORD_CANDIDATES:
            if keyword in preference_text:
                preferences.append(keyword)

        return preferences

    def _parse_keywords(
        self,
        query_lower: str,
        preferences: list[str] | None = None,
    ) -> list[str]:
        """
        Parse hard keyword requirements.

        Keywords explicitly identified as soft preferences are excluded
        so they do not become SQL search filters.
        """

        preference_set = set(
            preferences or []
        )

        return [
            keyword
            for keyword in self.KEYWORD_CANDIDATES
            if keyword in query_lower
            and keyword not in preference_set
        ]