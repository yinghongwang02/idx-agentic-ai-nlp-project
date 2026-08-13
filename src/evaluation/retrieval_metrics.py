from __future__ import annotations

from typing import Iterable

from src.schemas.listing_schema import ListingSchema
from src.evaluation.retrieval_cases import (
    RetrievalEvaluationCase,
)


def satisfies_hard_constraints(
    listing: ListingSchema,
    case: RetrievalEvaluationCase,
) -> bool:
    if case.city:
        if listing.city.lower() != case.city.lower():
            return False

    if case.max_price is not None:
        if listing.list_price > case.max_price:
            return False

    if case.min_bedrooms is not None:
        bedrooms = listing.bedrooms_total

        if bedrooms is None:
            return False

        if bedrooms < case.min_bedrooms:
            return False

    if case.min_bathrooms is not None:
        bathrooms = listing.bathrooms_total_integer

        if bathrooms is None:
            return False

        if bathrooms < case.min_bathrooms:
            return False

    if case.property_type:
        actual_type = (
            listing.property_sub_type or ""
        ).lower()

        if case.property_type.lower() not in actual_type:
            return False

    return True


def hard_constraint_pass_rate(
    listings: Iterable[ListingSchema],
    case: RetrievalEvaluationCase,
) -> float:
    listings = list(listings)

    if not listings:
        return 0.0

    passed = sum(
        satisfies_hard_constraints(
            listing,
            case,
        )
        for listing in listings
    )

    return passed / len(listings)


def listing_has_preference_term(
    listing: ListingSchema,
    terms: list[str],
) -> bool:
    remarks = (
        listing.public_remarks or ""
    ).lower()

    return any(
        term.lower() in remarks
        for term in terms
    )


def preference_term_hit_rate(
    listings: Iterable[ListingSchema],
    terms: list[str],
) -> float:
    listings = list(listings)

    if not listings:
        return 0.0

    hits = sum(
        listing_has_preference_term(
            listing,
            terms,
        )
        for listing in listings
    )

    return hits / len(listings)