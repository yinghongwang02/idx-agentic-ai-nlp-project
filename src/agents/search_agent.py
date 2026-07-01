from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.search.search_repository import SearchRepository


class SearchAgent:
    def __init__(self, repository: SearchRepository) -> None:
        self.repository = repository

    def run(self, intent: PropertyIntent, limit: int = 5) -> list[ListingSchema]:
        return self.repository.search(intent=intent, limit=limit)