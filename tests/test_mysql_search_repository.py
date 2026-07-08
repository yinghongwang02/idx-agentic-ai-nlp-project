from unittest.mock import MagicMock, patch

from src.search.mysql_search_repository import MySQLSearchRepository
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


def test_mysql_repository_search():
    fake_row = {
        "L_ListingID": "123",
        "L_DisplayId": "A1",
        "L_Address": "123 Main",
        "L_City": "Irvine",
        "L_State": "CA",
        "L_Zip": "92618",
        "L_SystemPrice": 800000,
        "L_Keyword2": 3,
        "LM_Dec_3": 2,
        "LM_Int2_3": 1500,
        "L_Type_": "Condominium",
        "DaysOnMarket": 10,
        "AssociationFee": 300,
        "L_Remarks": "Nice home",
        "L_Photos": None,
        "PhotoCount": 10,
        "LMD_MP_Latitude": 33.6,
        "LMD_MP_Longitude": -117.8,
        "L_Class": "Residential",
        "L_Status": "Active",
    }

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [fake_row]

    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor

    with patch(
        "mysql.connector.connect",
        return_value=mock_connection,
    ):
        repo = MySQLSearchRepository()

        intent = PropertyIntent(
            city="Irvine",
            max_price=900000,
            min_bedrooms=3,
            keywords=[],
        )

        listings = repo.search(intent)

    assert len(listings) == 1
    assert isinstance(listings[0], ListingSchema)

    mock_cursor.execute.assert_called_once()