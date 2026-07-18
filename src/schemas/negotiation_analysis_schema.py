from pydantic import BaseModel


class NegotiationAnalysis(BaseModel):
    """
    Structured negotiation analysis for one active listing.
    """

    negotiation_score: float

    dom_score: float
    price_position_score: float
    sale_to_list_score: float
    hoa_score: float

    signals: list[str]