from typing import Any

from src.schemas.listing_schema import ListingSchema


def format_mysql_listing(row: dict[str, Any]) -> ListingSchema:
    """
    Convert one MySQL rets_property row into ListingSchema.
    """

    record = {
        "listing_key": row.get("L_ListingID"),
        "display_id": row.get("L_DisplayId"),
        "unparsed_address": row.get("L_Address"),
        "city": row.get("L_City"),
        "state_or_province": row.get("L_State"),
        "postal_code": str(row.get("L_Zip")) if row.get("L_Zip") is not None else None,
        "list_price": row.get("L_SystemPrice"),
        "bedrooms_total": row.get("L_Keyword2"),
        "bathrooms_total_integer": row.get("LM_Dec_3"),
        "living_area": row.get("LM_Int2_3"),
        "property_sub_type": row.get("L_Type_"),
        "days_on_market": row.get("DaysOnMarket"),
        "association_fee": row.get("AssociationFee"),
        "public_remarks": row.get("L_Remarks"),
        "photos": row.get("L_Photos"),
        "photo_count": row.get("PhotoCount"),
        "latitude": row.get("LMD_MP_Latitude"),
        "longitude": row.get("LMD_MP_Longitude"),
        "property_type": row.get("L_Class"),
        "standard_status": row.get("L_Status"),
    }

    return ListingSchema(**record)