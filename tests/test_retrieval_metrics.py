from src.evaluation.retrieval_cases import (
    RetrievalEvaluationCase,
)
from src.evaluation.retrieval_metrics import (
    hard_constraint_pass_rate,
    preference_term_hit_rate,
)
from src.schemas.listing_schema import ListingSchema


def make_listing(
    *,
    city: str = "Irvine",
    price: float = 1_000_000,
    bedrooms: int = 3,
    property_type: str = (
        "SingleFamilyResidence"
    ),
    remarks: str = "",
) -> ListingSchema:
    return ListingSchema(
        listing_key="1",
        unparsed_address="1 Main St",
        city=city,
        list_price=price,
        bedrooms_total=bedrooms,
        property_sub_type=(
            property_type
        ),
        public_remarks=remarks,
    )


def test_hard_constraint_pass_rate() -> None:
    case = RetrievalEvaluationCase(
        name="test",
        city="Irvine",
        max_price=1_300_000,
        min_bedrooms=3,
        property_type=(
            "SingleFamilyResidence"
        ),
    )

    listings = [
        make_listing(),
        make_listing(
            city="Los Angeles"
        ),
    ]

    assert (
        hard_constraint_pass_rate(
            listings,
            case,
        )
        == 0.5
    )


def test_preference_term_hit_rate() -> None:
    listings = [
        make_listing(
            remarks=(
                "Beautiful pool home."
            )
        ),
        make_listing(
            remarks=(
                "Large backyard."
            )
        ),
    ]

    rate = preference_term_hit_rate(
        listings,
        ["pool"],
    )

    assert rate == 0.5