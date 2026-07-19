from abc import ABC, abstractmethod

from src.schemas.comparable_result_schema import ComparableResult
from src.schemas.sold_comp_schema import SoldCompSchema
from src.schemas.listing_schema import ListingSchema

class SoldCompRepository(ABC):
    """
    Abstract repository interface for sold comparable properties.
    """

    @abstractmethod
    def find_recent_comps(
        self,
        city: str,
        postal_code: str | None = None,
        months: int = 12,
        limit: int = 500,
    ) -> list[SoldCompSchema]:
        """
        Return recent sold comparable properties.

        Args:
            city:
                Required city used as the primary market filter.

            postal_code:
                Optional ZIP code for narrower comparable searches.

            months:
                Lookback window in months.

            limit:
                Maximum number of sold records returned.

        Returns:
            A list of normalized SoldCompSchema objects.
        """
        raise NotImplementedError

    @abstractmethod
    def find_similar_comps(
        self,
        listing: ListingSchema,
        months: int = 12,
        limit: int = 100,
        minimum_comps: int = 5,
    ) -> ComparableResult:
        """
        Find comparable sold properties using progressive fallback.

        Match levels:

        strict:
            city + ZIP + property type
            + beds +/- 1
            + baths +/- 1
            + sqft +/- 20%

        relaxed:
            city + property type
            + beds +/- 1
            + baths +/- 1
            + sqft +/- 25%

        broad:
            city + property type

        market_fallback:
            city-level recent sold properties
        """
        raise NotImplementedError