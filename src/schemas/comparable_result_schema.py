from pydantic import BaseModel

from src.schemas.sold_comp_schema import SoldCompSchema


class ComparableResult(BaseModel):
    """
    Result of comparable property matching with fallback metadata.
    """

    comps: list[SoldCompSchema]

    match_level: str

    comp_count: int