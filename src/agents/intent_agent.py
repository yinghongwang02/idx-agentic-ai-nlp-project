import re

from src.schemas.intent_schema import PropertyIntent


class IntentAgent:
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
        query_lower = query.lower()

        return PropertyIntent(
            city=self._parse_city(query_lower),
            max_price=self._parse_max_price(query_lower),
            min_bedrooms=self._parse_min_bedrooms(query_lower),
            min_bathrooms=self._parse_min_bathrooms(query_lower),
            property_type=self._parse_property_type(query_lower),
            keywords=self._parse_keywords(query_lower),
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

    def _parse_keywords(self, query_lower: str) -> list[str]:
        return [
            keyword
            for keyword in self.KEYWORD_CANDIDATES
            if keyword in query_lower
        ]