from src.agents.intent_agent import IntentAgent
from src.search.csv_search_repository import CSVSearchRepository


def main() -> None:
    agent = IntentAgent()
    repository = CSVSearchRepository("data/sample_listings.csv")

    queries = [
        "Show me 3 bedroom condos in Irvine under 900k",
        "Find single family homes in Irvine under 1.3m with a backyard",
        "Find townhouses with garage",
        "Luxury condos in Los Angeles under 1m with views",
        "Show 3 bedroom homes in Irvine close to schools",
        "Show condos in Irvine", 
        "Find single family homes in Irvine", 
        " Find 4 bedroom homes", 
        " Show homes with at least 2 bathrooms", 
        " Find homes in Los Angeles", 
        " Find townhouses in Anaheim", 
    ]

    for query in queries:
        intent = agent.run(query)
        listings = repository.search(intent, limit=5)

        print("=" * 80)
        print(f"Query: {query}")
        print(f"Parsed intent: {intent.model_dump()}")
        print(f"Number of results: {len(listings)}")

        for listing in listings:
            print(
                f"- {listing.listing_id}: "
                f"{listing.bedrooms_total} bed / "
                f"{listing.bathrooms_total_integer} bath in "
                f"{listing.city} for ${listing.list_price:,.0f}"
            )


if __name__ == "__main__":
    main()