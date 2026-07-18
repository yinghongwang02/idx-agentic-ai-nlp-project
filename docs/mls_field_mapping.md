# Database Tables

The local MySQL database `idx_exchange` currently contains three MLS tables.

| Table | Description 
|---------------|-----------------------------
| rets_property | Active residential listings 
| california_sold | Historical sold transactions 
| rets_openhouse | Upcoming open houses 

The project currently uses `rets_property` as the primary search source.

The project currently uses:

- `rets_property` → active property search
- `california_sold` → sold comparable retrieval and market analytics
- `rets_openhouse` → reserved for future open house search and recommendations

---

# MLS Field Mapping

This document maps the internal IDX SQL schema to the corresponding MLS API (RESO/Trestle) fields.

The production database uses historical IDX field names (e.g. `L_SystemPrice`, `L_Keyword2`, `LM_Int2_3`), while API responses and documentation typically use standardized RESO field names (e.g. `ListPrice`, `BedroomsTotal`, `LivingArea`).

Search agents, query builders, and future RAG components should treat the API field names as the canonical business concepts and translate them into SQL fields when querying MySQL.

---

## Property Information

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_ListingID | ListingKey | Listing identifier |
| L_DisplayId | ListingKey | Display identifier |
| L_Address | UnparsedAddress | Full property address |
| L_AddressStreet | StreetName | Street name |
| L_City | City | City |
| L_State | StateOrProvince | State |
| L_Zip | PostalCode | ZIP code |

---

## Property Attributes

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_Class | PropertyType | Property type |
| L_Type_ | PropertySubType | Property subtype |
| L_Keyword2 | BedroomsTotal | Number of bedrooms |
| LM_Dec_3 | BathroomsTotalInteger | Number of bathrooms |
| LM_Int2_3 | LivingArea | Living area (sqft) |
| L_Keyword1 | LotSizeArea | Lot size |
| L_Keyword5 | GarageSpaces | Garage spaces |
| L_Keyword7 | Levels | Number of levels |
| YearBuilt | YearBuilt | Year built |
| MainLevelBedrooms | MainLevelBedrooms | Bedrooms on main level |
| NewConstructionYN | NewConstructionYN | New construction |

---

## Pricing

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_SystemPrice | ListPrice | Current listing price |
| AssociationFee | AssociationFee | HOA fee |
| AssociationFeeFrequency | AssociationFeeFrequency | HOA frequency |

---

## Sold Comparable Fields

The `california_sold` table uses standardized MLS/RESO-style field names and supports Week 5 market analytics and comparable sales analysis.

| Sold Field | Canonical Concept | Description |
|------------|-------------------|-------------|
| ListingKey | listing_key | Sold listing identifier |
| UnparsedAddress | unparsed_address | Full property address |
| City | city | City |
| PostalCode | postal_code | ZIP code |
| PropertySubType | property_sub_type | Property subtype |
| BedroomsTotal | bedrooms_total | Number of bedrooms |
| BathroomsTotalInteger | bathrooms_total_integer | Number of bathrooms |
| LivingArea | living_area | Living area in square feet |
| OriginalListPrice | original_list_price | Original listing price |
| ListPrice | list_price | Final listing price before sale |
| ClosePrice | close_price | Final sale price |
| CloseDate | close_date | Sale closing date |
| DaysOnMarket | days_on_market | Number of days on market |
| AssociationFee | association_fee | HOA fee |

These fields are normalized into `SoldCompSchema` before being used by the market analytics and negotiation modules.

The initial sold comparable repository supports recent comparable retrieval by city, with optional ZIP code filtering and a configurable lookback window.

---

## Listing Status

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_Status | MlsStatus | Listing status |
| ListingContractDate | ListingContractDate | Listing contract date |
| ModificationTimestamp | ModificationTimestamp | Last modification |

---

## Location

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| LMD_MP_Latitude | Latitude | Latitude |
| LMD_MP_Longitude | Longitude | Longitude |
| HighSchoolDistrict | HighSchoolDistrict | School district |
| SubdivisionName | SubdivisionName | Community |

---

## Listing Description

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_Remarks | PublicRemarks | Public remarks |
| Flooring | Flooring | Flooring |
| FireplaceYN | FireplaceYN | Fireplace |
| ViewYN | ViewYN | View |
| PoolPrivateYN | PoolPrivateYN | Pool |
| Fencing | Fencing | Fence |

---

## Listing Media

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| L_Photos | Images | Listing images |
| PhotoCount | PhotosCount | Number of photos |

---

## Listing Agent

| SQL Field | API Field | Description |
|------------|-----------|-------------|
| LA1_UserFirstName | ListAgentFirstName | Agent first name |
| LA1_UserLastName | ListAgentLastName | Agent last name |
| LO1_OrganizationName | ListOfficeName | Listing office |

---

## Search Layer Convention

Within this project, the natural language parser should produce canonical property concepts:

```python
PropertyIntent(
    city="Irvine",
    max_price=900000,
    bedrooms=3,
    bathrooms=2,
    property_type="Residential"
)
```

The SQL Builder is responsible for translating those concepts into SQL fields:

| Canonical Concept | SQL Column |
|------------------|------------|
| city | L_City |
| max_price | L_SystemPrice |
| bedrooms | L_Keyword2 |
| bathrooms | LM_Dec_3 |
| living_area | LM_Int2_3 |
| property_type | L_Type_ |

This keeps the parser independent of the underlying database schema.