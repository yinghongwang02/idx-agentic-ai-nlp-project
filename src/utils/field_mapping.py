"""
MLS field mapping.

This module defines the canonical property concepts used throughout the
application and maps them to the internal IDX MySQL schema.

IntentAgent
        ↓
PropertyIntent
        ↓
QueryBuilder
        ↓
MLS_FIELD_MAPPING
        ↓
Parameterized SQL
"""

from typing import Final


# ---------------------------------------------------------------------
# Canonical Property Fields
# ---------------------------------------------------------------------

CANONICAL_FIELDS: Final[set[str]] = {
    "listing_id",
    "display_id",
    "address",
    "city",
    "state",
    "zip",
    "property_class",
    "property_type",
    "bedrooms",
    "bathrooms",
    "living_area",
    "lot_size",
    "garage_spaces",
    "levels",
    "list_price",
    "remarks",
    "photos",
    "latitude",
    "longitude",
    "status",
    "days_on_market",
    "association_fee",
    "association_fee_frequency",
    "pool",
    "view",
    "year_built",
    "fireplace",
    "flooring",
    "subdivision",
    "high_school_district",
    "listing_contract_date",
    "modification_timestamp",
    "agent_first_name",
    "agent_last_name",
    "office_name",
}


# ---------------------------------------------------------------------
# Canonical -> MySQL Column
# ---------------------------------------------------------------------

MLS_FIELD_MAPPING: Final[dict[str, str]] = {

    # -------------------------
    # Identifiers
    # -------------------------
    "listing_id": "L_ListingID",
    "display_id": "L_DisplayId",

    # -------------------------
    # Address
    # -------------------------
    "address": "L_Address",
    "street": "L_AddressStreet",
    "city": "L_City",
    "state": "L_State",
    "zip": "L_Zip",

    # -------------------------
    # Property
    # -------------------------
    "property_class": "L_Class",
    "property_type": "L_Type_",
    "bedrooms": "L_Keyword2",
    "bathrooms": "LM_Dec_3",
    "living_area": "LM_Int2_3",
    "lot_size": "L_Keyword1",
    "garage_spaces": "L_Keyword5",
    "levels": "L_Keyword7",
    "year_built": "YearBuilt",

    # -------------------------
    # Pricing
    # -------------------------
    "list_price": "L_SystemPrice",
    "association_fee": "AssociationFee",
    "association_fee_frequency": "AssociationFeeFrequency",

    # -------------------------
    # Listing Status
    # -------------------------
    "status": "L_Status",
    "listing_contract_date": "ListingContractDate",
    "modification_timestamp": "ModificationTimestamp",
    "days_on_market": "DaysOnMarket",

    # -------------------------
    # Description
    # -------------------------
    "remarks": "L_Remarks",
    "flooring": "Flooring",
    "pool": "PoolPrivateYN",
    "view": "ViewYN",
    "fireplace": "FireplaceYN",

    # -------------------------
    # Media
    # -------------------------
    "photos": "L_Photos",
    "photo_count": "PhotoCount",

    # -------------------------
    # Location
    # -------------------------
    "latitude": "LMD_MP_Latitude",
    "longitude": "LMD_MP_Longitude",
    "subdivision": "SubdivisionName",
    "high_school_district": "HighSchoolDistrict",

    # -------------------------
    # Listing Agent
    # -------------------------
    "agent_first_name": "LA1_UserFirstName",
    "agent_last_name": "LA1_UserLastName",
    "office_name": "LO1_OrganizationName",
}


# ---------------------------------------------------------------------
# Reverse Mapping (MySQL -> Canonical)
# ---------------------------------------------------------------------

REVERSE_MLS_FIELD_MAPPING: Final[dict[str, str]] = {
    value: key
    for key, value in MLS_FIELD_MAPPING.items()
}


# ---------------------------------------------------------------------
# Frequently Used SQL Columns
# ---------------------------------------------------------------------

SEARCH_COLUMNS: Final[list[str]] = [
    MLS_FIELD_MAPPING["listing_id"],
    MLS_FIELD_MAPPING["display_id"],
    MLS_FIELD_MAPPING["address"],
    MLS_FIELD_MAPPING["city"],
    MLS_FIELD_MAPPING["state"],
    MLS_FIELD_MAPPING["zip"],
    MLS_FIELD_MAPPING["property_type"],
    MLS_FIELD_MAPPING["list_price"],
    MLS_FIELD_MAPPING["bedrooms"],
    MLS_FIELD_MAPPING["bathrooms"],
    MLS_FIELD_MAPPING["living_area"],
    MLS_FIELD_MAPPING["days_on_market"],
    MLS_FIELD_MAPPING["remarks"],
]


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def sql_column(field_name: str) -> str:
    """
    Convert canonical field name to MySQL column.

    Example
    -------
    sql_column("city")
    -> "L_City"
    """
    return MLS_FIELD_MAPPING[field_name]


def canonical_name(sql_column_name: str) -> str:
    """
    Convert MySQL column back to canonical field name.

    Example
    -------
    canonical_name("L_SystemPrice")
    -> "list_price"
    """
    return REVERSE_MLS_FIELD_MAPPING[sql_column_name]