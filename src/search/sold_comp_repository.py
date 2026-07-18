from abc import ABC, abstractmethod

from src.schemas.sold_comp_schema import SoldCompSchema


class SoldCompRepository(ABC):
    """
    Abstract repository interface for sold comparable properties.

    Implementations are responsible for retrieving normalized sold comp
    records without exposing database-specific logic to MarketAgent.
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