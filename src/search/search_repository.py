from abc import ABC, abstractmethod

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class SearchRepository(ABC):
    @abstractmethod
    def search(self, intent: PropertyIntent, limit: int = 5) -> list[ListingSchema]:
        raise NotImplementedError