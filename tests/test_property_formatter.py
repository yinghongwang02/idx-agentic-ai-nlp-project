from src.search.property_formatter import format_mysql_listing
from src.schemas.listing_schema import ListingSchema


def test_format_mysql_listing_returns_listing_schema():
    row = {
        "L_ListingID": "1156793628",
        "L_DisplayId": "OC123456",
        "L_Address": "123 Main St",
        "L_City": "Irvine",
        "L_State": "CA",
        "L_Zip": "92618",
        "L_SystemPrice": 735000,
        "L_Keyword2": 3,
        "LM_Dec_3": 2,
        "LM_Int2_3": 1500,
        "L_Type_": "Condominium",
        "DaysOnMarket": 12,
        "AssociationFee": 300,
        "L_Remarks": "Beautiful condo in Irvine",
        "L_Photos": None,
        "PhotoCount": 10,
        "LMD_MP_Latitude": 33.6846,
        "LMD_MP_Longitude": -117.8265,
        "L_Class": "Residential",
        "L_Status": "Active",
    }

    listing = format_mysql_listing(row)

    assert isinstance(listing, ListingSchema)
    assert listing.listing_key == "1156793628"
    assert listing.city == "Irvine"
    assert listing.list_price == 735000
    assert listing.bedrooms_total == 3
    assert listing.property_sub_type == "Condominium"