from src.schemas.intent_schema import PropertyIntent


class IntentAgent:
    def run(self, user_query: str) -> PropertyIntent:
        query = user_query.lower()

        intent = PropertyIntent()

        if "irvine" in query:
            intent.city = "Irvine"

        if "3" in query and "bed" in query:
            intent.min_bedrooms = 3

        if "900k" in query or "900,000" in query:
            intent.max_price = 900000

        return intent