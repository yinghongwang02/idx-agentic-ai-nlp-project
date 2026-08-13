from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    name: str

    city: str | None = None
    max_price: int | None = None
    min_bedrooms: int | None = None
    min_bathrooms: float | None = None
    property_type: str | None = None

    semantic_query: str = ""

    # Simple lexical terms used only for lightweight MVP diagnostics.
    preference_terms: list[str] = field(
        default_factory=list
    )


RETRIEVAL_CASES = [
    RetrievalEvaluationCase(
        name="lancaster_pool_open_layout",
        city="Lancaster",
        max_price=2_000_000,
        min_bedrooms=3,
        semantic_query="pool, open floor plan",
        preference_terms=[
            "pool",
            "open floor plan",
            "open concept",
            "open-concept",
        ],
    ),
    RetrievalEvaluationCase(
        name="san_jose_bright_modern_condo",
        city="San Jose",
        max_price=1_000_000,
        min_bedrooms=1,
        property_type="Condominium",
        semantic_query="bright home, modern living",
        preference_terms=[
            "bright",
            "natural light",
            "modern",
            "remodeled",
        ],
    ),
    RetrievalEvaluationCase(
        name="los_angeles_modern_open_layout",
        city="Los Angeles",
        max_price=5_000_000,
        min_bedrooms=3,
        property_type="SingleFamilyResidence",
        semantic_query="modern design, open floor plan",
        preference_terms=[
            "modern",
            "open floor plan",
            "open concept",
            "open-concept",
        ],
    ),
]