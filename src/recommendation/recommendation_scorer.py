from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.schemas.market_summary_schema import MarketSummary
from src.schemas.negotiation_analysis_schema import NegotiationAnalysis
from src.schemas.recommendation_score_schema import RecommendationScore


def calculate_search_match_score(
    listing: ListingSchema,
    intent: PropertyIntent,
) -> float:
    scores: list[float] = []

    if intent.city:
        scores.append(
            100.0
            if listing.city
            and listing.city.lower() == intent.city.lower()
            else 0.0
        )

    if intent.max_price is not None:
        scores.append(
            100.0
            if listing.list_price is not None
            and listing.list_price <= intent.max_price
            else 0.0
        )

    if intent.min_bedrooms is not None:
        scores.append(
            100.0
            if listing.bedrooms_total is not None
            and listing.bedrooms_total >= intent.min_bedrooms
            else 0.0
        )

    if intent.min_bathrooms is not None:
        scores.append(
            100.0
            if listing.bathrooms_total_integer is not None
            and listing.bathrooms_total_integer >= intent.min_bathrooms
            else 0.0
        )

    if intent.property_type:
        scores.append(
            100.0
            if listing.property_sub_type
            and listing.property_sub_type.lower()
            == intent.property_type.lower()
            else 0.0
        )

    if not scores:
        return 50.0

    return sum(scores) / len(scores)


def calculate_market_score(
    market_summary: MarketSummary,
) -> float:
    score = 50.0

    sale_to_list_ratio = (
        market_summary.average_sale_to_list_ratio
    )

    if sale_to_list_ratio is not None:
        if sale_to_list_ratio < 0.95:
            score += 30.0
        elif sale_to_list_ratio < 0.98:
            score += 20.0
        elif sale_to_list_ratio < 1.00:
            score += 10.0
        elif sale_to_list_ratio > 1.02:
            score -= 20.0

    average_dom = market_summary.average_days_on_market

    if average_dom is not None:
        if average_dom >= 60:
            score += 20.0
        elif average_dom >= 40:
            score += 10.0
        elif average_dom < 20:
            score -= 10.0

    return max(0.0, min(score, 100.0))


def calculate_recommendation_score(
    listing: ListingSchema,
    intent: PropertyIntent,
    market_summary: MarketSummary,
    negotiation_analysis: NegotiationAnalysis,
) -> RecommendationScore:
    search_match_score = calculate_search_match_score(
        listing=listing,
        intent=intent,
    )

    market_score = calculate_market_score(
        market_summary=market_summary,
    )

    overall_score = (
        search_match_score * 0.45
        + negotiation_analysis.negotiation_score * 0.35
        + market_score * 0.20
    )

    reasons: list[str] = []

    if search_match_score >= 80:
        reasons.append(
            "The listing strongly matches the buyer's search criteria."
        )

    if negotiation_analysis.negotiation_score >= 70:
        reasons.append(
            "The listing shows relatively strong negotiation potential."
        )
    elif negotiation_analysis.negotiation_score >= 50:
        reasons.append(
            "The listing shows moderate negotiation potential."
        )

    if market_score >= 70:
        reasons.append(
            "Recent market conditions appear relatively favorable for buyers."
        )
    elif market_score >= 50:
        reasons.append(
            "Recent market conditions are moderately favorable for buyers."
        )

    if overall_score >= 80:
        recommendation_label = "Strong Recommendation"
    elif overall_score >= 65:
        recommendation_label = "Good Recommendation"
    elif overall_score >= 50:
        recommendation_label = "Moderate Recommendation"
    else:
        recommendation_label = "Low Priority"

    return RecommendationScore(
        overall_score=round(overall_score, 2),
        search_match_score=round(search_match_score, 2),
        negotiation_score=round(
            negotiation_analysis.negotiation_score,
            2,
        ),
        market_score=round(market_score, 2),
        recommendation_label=recommendation_label,
        reasons=reasons,
    )