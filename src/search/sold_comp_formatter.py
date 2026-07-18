from typing import Any

from src.schemas.sold_comp_schema import SoldCompSchema


def format_mysql_sold_comp(row: dict[str, Any]) -> SoldCompSchema:
    """
    Convert one MySQL california_sold row into SoldCompSchema.
    """

    record = {
        "listing_key": str(row.get("ListingKey"))
        if row.get("ListingKey") is not None
        else "",
        "city": row.get("City"),
        "postal_code": (
            str(row.get("PostalCode"))
            if row.get("PostalCode") is not None
            else None
        ),
        "unparsed_address": row.get("UnparsedAddress"),
        "property_sub_type": row.get("PropertySubType"),
        "bedrooms_total": row.get("BedroomsTotal"),
        "bathrooms_total_integer": row.get("BathroomsTotalInteger"),
        "living_area": row.get("LivingArea"),
        "list_price": row.get("ListPrice"),
        "original_list_price": row.get("OriginalListPrice"),
        "close_price": row.get("ClosePrice"),
        "close_date": row.get("CloseDate"),
        "days_on_market": row.get("DaysOnMarket"),
        "association_fee": row.get("AssociationFee"),
    }

    return SoldCompSchema(**record)