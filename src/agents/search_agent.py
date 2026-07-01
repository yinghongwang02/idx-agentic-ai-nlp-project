import pandas as pd

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class SearchAgent:
    def __init__(self, data_path: str = "data/sample_listings.csv") -> None:
        self.data_path = data_path

    def run(self, intent: PropertyIntent) -> list[ListingSchema]:
        df = pd.read_csv(self.data_path)

        if intent.city:
            df = df[df["city"].str.lower() == intent.city.lower()]

        if intent.max_price:
            df = df[df["list_price"] <= intent.max_price]

        if intent.min_bedrooms:
            df = df[df["bedrooms_total"] >= intent.min_bedrooms]

        if intent.min_bathrooms:
            df = df[df["bathrooms_total_integer"] >= intent.min_bathrooms]

        if intent.property_type:
            df = df[
                df["property_sub_type"]
                .fillna("")
                .str.lower()
                .str.contains(intent.property_type.lower())
            ]

        # Convert pandas NaN values to None for Pydantic
        df = df.where(pd.notnull(df), None)

        records = df.head(5).to_dict(orient="records")

        # Normalize fields that should be strings
        for record in records:
            if record.get("postal_code") is not None:
                record["postal_code"] = str(record["postal_code"])

            if record.get("close_date") is not None:
                record["close_date"] = str(record["close_date"])

        return [ListingSchema(**record) for record in records]