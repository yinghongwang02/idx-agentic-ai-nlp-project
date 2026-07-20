from pydantic import BaseModel


class PreferenceMatchAnalysis(BaseModel):
    """
    Soft preference match analysis for one active listing.
    """

    preference_match_score: float

    requested_preferences: list[str]
    matched_preferences: list[str]
    unmatched_preferences: list[str]

    signals: list[str]