from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.schemas.preference_match_analysis_schema import (
    PreferenceMatchAnalysis,
)


class PreferenceMatchAgent:
    """
    Evaluate how well an active listing matches the buyer's
    soft preferences.

    Hard constraints such as city, price, bedrooms, bathrooms,
    property type, and required keywords are intentionally excluded.
    """

    def run(
        self,
        listing: ListingSchema,
        intent: PropertyIntent,
    ) -> PreferenceMatchAnalysis:
        requested_preferences = [
            preference.lower().strip()
            for preference in (intent.preferences or [])
            if preference.strip()
        ]

        if not requested_preferences:
            return PreferenceMatchAnalysis(
                preference_match_score=50.0,
                requested_preferences=[],
                matched_preferences=[],
                unmatched_preferences=[],
                signals=[
                    "No soft preferences were provided, so preference match is neutral."
                ],
            )

        searchable_text = self._build_searchable_text(
            listing=listing,
        )

        matched_preferences: list[str] = []
        unmatched_preferences: list[str] = []

        for preference in requested_preferences:
            if self._matches_preference(
                preference=preference,
                searchable_text=searchable_text,
            ):
                matched_preferences.append(
                    preference
                )
            else:
                unmatched_preferences.append(
                    preference
                )

        preference_match_score = (
            len(matched_preferences)
            / len(requested_preferences)
            * 100
        )

        signals = self._build_signals(
            matched_preferences=matched_preferences,
            unmatched_preferences=unmatched_preferences,
        )

        return PreferenceMatchAnalysis(
            preference_match_score=round(
                preference_match_score,
                2,
            ),
            requested_preferences=requested_preferences,
            matched_preferences=matched_preferences,
            unmatched_preferences=unmatched_preferences,
            signals=signals,
        )

    @staticmethod
    def _build_searchable_text(
        listing: ListingSchema,
    ) -> str:
        """
        Combine listing text fields that may contain
        soft preference information.
        """

        parts = [
            listing.public_remarks or "",
            listing.property_sub_type or "",
        ]

        return " ".join(parts).lower()

    @staticmethod
    def _matches_preference(
        preference: str,
        searchable_text: str,
    ) -> bool:
        """
        Match one normalized preference against listing text.

        Aliases allow related wording in MLS remarks to satisfy
        the same buyer preference.
        """

        preference_aliases = {
            "garage": [
                "garage",
                "attached garage",
                "detached garage",
            ],
            "parking": [
                "parking",
                "carport",
            ],
            "pool": [
                "pool",
                "swimming pool",
            ],
            "spa": [
                "spa",
                "hot tub",
            ],
            "view": [
                "view",
                "views",
                "ocean view",
                "mountain view",
                "city view",
            ],
            "backyard": [
                "backyard",
                "back yard",
                "yard",
            ],
            "patio": [
                "patio",
                "courtyard",
            ],
            "balcony": [
                "balcony",
            ],
            "fireplace": [
                "fireplace",
            ],
            "modern": [
                "modern",
                "contemporary",
                "updated",
                "renovated",
                "remodeled",
            ],
            "shopping": [
                "shopping",
                "shops",
                "retail",
            ],
            "parks": [
                "park",
                "parks",
                "greenbelt",
            ],
            "school": [
                "school",
                "schools",
                "school district",
            ],
            "schools": [
                "school",
                "schools",
                "school district",
            ],
            "luxury": [
                "luxury",
                "luxurious",
                "high-end",
            ],
        }

        aliases = preference_aliases.get(
            preference,
            [preference],
        )

        return any(
            alias in searchable_text
            for alias in aliases
        )

    @staticmethod
    def _build_signals(
        matched_preferences: list[str],
        unmatched_preferences: list[str],
    ) -> list[str]:
        signals: list[str] = []

        if matched_preferences:
            signals.append(
                "Matched soft preferences: "
                + ", ".join(
                    matched_preferences
                )
                + "."
            )

        if unmatched_preferences:
            signals.append(
                "Unmatched soft preferences: "
                + ", ".join(
                    unmatched_preferences
                )
                + "."
            )

        return signals