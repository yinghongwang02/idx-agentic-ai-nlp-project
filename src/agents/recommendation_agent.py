class RecommendationAgent:
    def run(self, listings: list[dict]) -> list[dict]:
        ranked = sorted(
            listings,
            key=lambda x: (
                x.get("days_on_market", 999),
                x.get("list_price", 999999999),
            ),
        )

        return ranked[:5]