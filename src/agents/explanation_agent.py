class ExplanationAgent:
    def run(self, recommendations: list[dict]) -> str:
        if not recommendations:
            return "No matching listings found."

        lines = ["Top matching listings:"]

        for item in recommendations:
            lines.append(
                f"- {item['listing_id']}: {item['bedrooms']} bed / "
                f"{item['bathrooms']} bath in {item['city']} "
                f"for ${item['list_price']:,.0f}. "
                f"Days on market: {item.get('days_on_market', 'N/A')}."
            )

        return "\n".join(lines)