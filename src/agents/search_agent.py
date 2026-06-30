import pandas as pd

from src.schemas.intent_schema import PropertyIntent


class SearchAgent:
    def __init__(self, data_path: str = "data/sample_listings.csv") -> None:
        self.data_path = data_path

    def run(self, intent: PropertyIntent) -> list[dict]:
        df = pd.read_csv(self.data_path)

        if intent.city:
            df = df[df["city"].str.lower() == intent.city.lower()]

        if intent.max_price:
            df = df[df["list_price"] <= intent.max_price]

        if intent.min_bedrooms:
            df = df[df["bedrooms"] >= intent.min_bedrooms]

        return df.head(5).to_dict(orient="records")