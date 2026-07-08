import pandas as pd

from src.search.csv_search_repository import CSVSearchRepository
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


def test_csv_repository_search(tmp_path):
    csv_path = tmp_path / "sample.csv"

    pd.DataFrame([
        {
            "listing_key": "LISTING-1",
            "unparsed_address": "123 Main",
            "city": "Irvine",
            "postal_code": "92618",
            "list_price": 800000,
            "bedrooms_total": 3,
            "bathrooms_total_integer": 2,
            "living_area": 1500,
            "property_sub_type": "Condominium",
            "property_type": "Residential",
            "standard_status": "Active",
            "days_on_market": 10,
            "association_fee": 300,
            "public_remarks": "Beautiful upgraded condo",
            "latitude": 33.6,
            "longitude": -117.8,
        }
    ]).to_csv(csv_path, index=False)

    repo = CSVSearchRepository(data_path=str(csv_path))

    intent = PropertyIntent(
        city="Irvine",
        max_price=900000,
        min_bedrooms=3,
        keywords=[],
    )

    listings = repo.search(intent)

    assert len(listings) == 1
    assert isinstance(listings[0], ListingSchema)
    assert listings[0].city == "Irvine"