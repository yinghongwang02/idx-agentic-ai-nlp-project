from typing import Any

from src.schemas.intent_schema import PropertyIntent
from src.utils.field_mapping import MLS_FIELD_MAPPING


class PropertyQueryBuilder:
    """
    Build parameterized SQL for property search.

    Responsibility:
        PropertyIntent -> SQL string + params list

    This class does not connect to MySQL.
    """

    DEFAULT_COLUMNS = [
        "L_ListingID",
        "L_DisplayId",
        "L_Address",
        "L_City",
        "L_State",
        "L_Zip",
        "L_SystemPrice",
        "L_Keyword2",
        "LM_Dec_3",
        "LM_Int2_3",
        "L_Type_",
        "DaysOnMarket",
        "AssociationFee",
        "L_Remarks",
        "L_Photos",
        "PhotoCount",
        "LMD_MP_Latitude",
        "LMD_MP_Longitude",
        "L_Class",
        "L_Status",
    ]

    def __init__(self, table_name: str = "rets_property") -> None:
        self.table_name = table_name

    def build(
        self,
        intent: PropertyIntent,
        limit: int = 5,
        offset: int = 0,
    ) -> tuple[str, list[Any]]:
        limit = self._sanitize_limit(limit)
        offset = max(offset, 0)

        sql_parts = [
            f"SELECT {', '.join(self.DEFAULT_COLUMNS)}",
            f"FROM {self.table_name}",
            "WHERE 1=1",
        ]

        params: list[Any] = []

        if intent.city:
            sql_parts.append(f"AND {MLS_FIELD_MAPPING['city']} = %s")
            params.append(intent.city)

        if intent.max_price:
            sql_parts.append(f"AND {MLS_FIELD_MAPPING['list_price']} <= %s")
            params.append(intent.max_price)

        if intent.min_bedrooms:
            sql_parts.append(f"AND {MLS_FIELD_MAPPING['bedrooms']} >= %s")
            params.append(intent.min_bedrooms)

        if intent.min_bathrooms:
            sql_parts.append(f"AND {MLS_FIELD_MAPPING['bathrooms']} >= %s")
            params.append(intent.min_bathrooms)

        if intent.property_type:
            sql_parts.append(f"AND {MLS_FIELD_MAPPING['property_type']} LIKE %s")
            params.append(f"%{intent.property_type}%")

        self._append_keyword_filters(sql_parts, params, intent.keywords)

        sql_parts.append(f"ORDER BY {MLS_FIELD_MAPPING['list_price']} ASC")
        sql_parts.append("LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        return "\n".join(sql_parts), params

    def _append_keyword_filters(
        self,
        sql_parts: list[str],
        params: list[Any],
        keywords: list[str],
    ) -> None:
        if not keywords:
            return

        for keyword in keywords:
            normalized = keyword.strip()
            if not normalized:
                continue

            sql_parts.append(f"AND {MLS_FIELD_MAPPING['remarks']} LIKE %s")
            params.append(f"%{normalized}%")

    @staticmethod
    def _sanitize_limit(limit: int) -> int:
        if limit <= 0:
            return 5
        return min(limit, 50)