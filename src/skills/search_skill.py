from src.agents.search_agent import SearchAgent
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.skills.base_skill import BaseSkill


class SearchSkill(BaseSkill):
    name = "property_search"

    def __init__(self) -> None:
        self.search_agent = SearchAgent()

    def run(self, input_data: PropertyIntent) -> list[ListingSchema]:
        return self.search_agent.run(input_data)