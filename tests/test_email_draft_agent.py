from __future__ import annotations

import pytest

from src.communication.email_draft_agent import (
    EmailDraftAgent,
)
from src.schemas.listing_schema import (
    ListingSchema,
)
from src.schemas.market_summary_schema import (
    MarketSummary,
)

from types import SimpleNamespace

# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def agent():
    return EmailDraftAgent()


@pytest.fixture
def irvine_listing():
    return ListingSchema(
        listing_key="1001",
        listing_id="OC260001",
        unparsed_address="123 Main Street",
        city="Irvine",
        postal_code="92618",
        standard_status="Active",
        property_type="Residential",
        property_sub_type=(
            "SingleFamilyResidence"
        ),
        list_price=1_250_000,
        bedrooms_total=3,
        bathrooms_total_integer=2,
        living_area=1_850,
        association_fee=150,
        days_on_market=18,
    )


@pytest.fixture
def second_irvine_listing():
    return ListingSchema(
        listing_key="1002",
        listing_id="OC260002",
        unparsed_address="456 Oak Avenue",
        city="Irvine",
        postal_code="92620",
        standard_status="Active",
        property_type="Residential",
        property_sub_type="Condominium",
        list_price=980_000,
        bedrooms_total=2,
        bathrooms_total_integer=2,
        living_area=1_420,
        association_fee=420,
        days_on_market=12,
    )


@pytest.fixture
def market_summary():
    return MarketSummary(
        city="Irvine",
        comp_count=48,
        median_close_price=1_180_000,
        average_days_on_market=24.5,
        average_sale_to_list_ratio=0.987,
        average_price_per_sqft=680.0,
    )


# =====================================================================
# Handbook approval status
# =====================================================================


def test_property_digest_is_pending_approval(
    agent,
    irvine_listing,
):
    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=[
            irvine_listing,
        ],
    )

    assert (
        draft.status
        == "pending_approval"
    )

    assert draft.to == (
        "buyer@example.com"
    )


# =====================================================================
# Property recommendation digest
# =====================================================================


def test_property_digest_contains_listing_details(
    agent,
    irvine_listing,
):
    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=[
            irvine_listing,
        ],
        buyer_preferences=(
            "Irvine under $1.5M"
        ),
    )

    assert (
        "Property Recommendations in Irvine"
        == draft.subject
    )

    assert (
        "123 Main Street"
        in draft.body
    )

    assert (
        "$1,250,000"
        in draft.body
    )

    assert "3 beds" in draft.body
    assert "2 baths" in draft.body
    assert "1,850 sqft" in draft.body

    assert (
        "Irvine under $1.5M"
        in draft.body
    )


# =====================================================================
# Recommendation result compatibility
# =====================================================================


def test_property_digest_accepts_recommendation_dicts(
    agent,
    irvine_listing,
):
    recommendation_result = {
        "listing": irvine_listing,
        "hybrid_similarity_score": 92.5,
        "comp_validation": {
            "status": "validated",
        },
    }

    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=[
            recommendation_result,
        ],
    )

    assert (
        "123 Main Street"
        in draft.body
    )

    assert (
        draft.metadata[
            "listing_count"
        ]
        == 1
    )


# =====================================================================
# Maximum five listings
# =====================================================================


def test_property_digest_respects_max_listings(
    agent,
    irvine_listing,
    second_irvine_listing,
):
    listings = [
        irvine_listing,
        second_irvine_listing,
        irvine_listing,
        second_irvine_listing,
        irvine_listing,
        second_irvine_listing,
    ]

    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=listings,
    )

    assert (
        draft.metadata[
            "listing_count"
        ]
        == 5
    )

    assert "5." in draft.body
    assert "6." not in draft.body


# =====================================================================
# Weekly market report
# =====================================================================


def test_weekly_market_report_uses_market_data(
    agent,
    market_summary,
):
    draft = (
        agent.draft_weekly_market_report(
            to="buyer@example.com",
            market_summary=market_summary,
        )
    )

    assert draft.status == (
        "pending_approval"
    )

    assert draft.subject == (
        "Weekly Real Estate Market Report — Irvine"
    )

    assert (
        "Comparable sales analyzed: 48"
        in draft.body
    )

    assert (
        "Median close price: $1,180,000"
        in draft.body
    )

    assert (
        "Average days on market: 24.5"
        in draft.body
    )

    assert (
        "Average sale-to-list ratio: 98.7%"
        in draft.body
    )

    assert (
        "Average price per square foot: $680"
        in draft.body
    )

    assert (
        draft.metadata[
            "draft_type"
        ]
        == "weekly_market_report"
    )


# =====================================================================
# Optional market snapshot in property digest
# =====================================================================


def test_property_digest_can_include_market_summary(
    agent,
    irvine_listing,
    market_summary,
):
    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=[
            irvine_listing,
        ],
        market_summary=market_summary,
    )

    assert (
        "Market Snapshot"
        in draft.body
    )

    assert (
        "Median close price: $1,180,000"
        in draft.body
    )


# =====================================================================
# Validation
# =====================================================================


def test_email_draft_rejects_empty_recipient(
    agent,
    irvine_listing,
):
    with pytest.raises(
        ValueError,
        match="recipient cannot be empty",
    ):
        agent.draft_property_digest(
            to="   ",
            listings=[
                irvine_listing,
            ],
        )


def test_property_digest_accepts_recommendation_objects(
    agent,
    irvine_listing,
):
    recommendation = SimpleNamespace(
        listing=irvine_listing,
        overall_score=91.5,
        recommendation_label="Strong Match",
    )

    draft = agent.draft_property_digest(
        to="buyer@example.com",
        listings=[
            recommendation,
        ],
    )

    assert (
        "123 Main Street"
        in draft.body
    )

    assert (
        draft.metadata[
            "listing_count"
        ]
        == 1
    )

    assert (
        draft.metadata["city"]
        == "Irvine"
    )