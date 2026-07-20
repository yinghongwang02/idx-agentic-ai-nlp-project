from pydantic import BaseModel


class NegotiationAnalysis(BaseModel):
    """
    Negotiation opportunity analysis for an active listing.

    Higher scores indicate stronger evidence of potential
    negotiation leverage.
    """

    negotiation_score: float

    dom_score: float
    sale_to_list_score: float

    signals: list[str]