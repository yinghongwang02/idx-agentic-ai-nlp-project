class ComplianceAgent:
    def run(self, user_query: str) -> str:
        risky_terms = ["race", "religion", "family status", "national origin"]

        query = user_query.lower()

        for term in risky_terms:
            if term in query:
                return "yellow"

        return "green"