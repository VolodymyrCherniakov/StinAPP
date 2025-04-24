from backend.app import declined_last_3_days, more_than_two_declines_in_last_5_days, app, get_stock_data
from unittest.mock import patch, MagicMock
from datetime import datetime

def test_declined_last_3_days():
    prices = [
        {"close": 90},
        {"close": 91},
        {"close": 92},
        {"close": 93}
    ]
    assert declined_last_3_days(prices[::-1]) is True
    assert declined_last_3_days(prices) is False

def test_more_than_two_declines_in_last_5_days():
    prices = [
        {"close": 100}, {"close": 99},
        {"close": 98}, {"close": 97},
        {"close": 96}, {"close": 95}
    ]
    assert more_than_two_declines_in_last_5_days(prices[::-1]) is True

@patch('app.client')
def test_get_stock_data(mock_client):
    mock_data = MagicMock()
    mock_data.empty = False
    mock_data.len.return_value = 6
    mock_data.sort_index.return_value.head.return_value.iterrows.return_value = [
        (datetime(2024, 4, 15), {'close': 150}),
        (datetime(2024, 4, 14), {'close': 152}),
    ]
    mock_client.get_dataframe.return_value = mock_data
    result = get_stock_data("AAPL")

    assert isinstance(result, list)
    assert len(result) > 0
    assert 'close' in result[0]

def test_hello_world():
    client = app.test_client()
    response = client.get('/api/hello')
    assert response.status_code == 200
    assert response.json == {"message": "Hello from Docker!"}