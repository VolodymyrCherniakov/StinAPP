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

@patch('backend.app.get_stock_data')
def test_get_stocks_success(mock_get_stock_data):
    mock_get_stock_data.return_value = [
        {"date": "2024-04-15", "close": 150},
        {"date": "2024-04-14", "close": 151},
        {"date": "2024-04-13", "close": 152},
        {"date": "2024-04-12", "close": 153},
        {"date": "2024-04-11", "close": 154},
        {"date": "2024-04-10", "close": 155},
    ]
    client = app.test_client()
    response = client.get('/api/stocks?tickers=AAPL')

    assert response.status_code == 200
    data = response.get_json()
    assert "AAPL" in data
    assert "declined_last_3_days" in data["AAPL"]
    assert "more_than_2_declines_last_5_days" in data["AAPL"]


@patch('backend.app.get_stock_data')
def test_get_stocks_error(mock_get_stock_data):
    mock_get_stock_data.return_value = {"error": "API limit exceeded"}
    client = app.test_client()
    response = client.get('/api/stocks?tickers=FAKE')

    assert response.status_code == 200
    data = response.get_json()
    assert "FAKE" in data
    assert "error" in data["FAKE"]

def test_handle_exception():
    with app.test_client() as client:
        @app.route('/cause_error')
        def cause_error():
            raise ValueError("Test Error")

        response = client.get('/cause_error')
        assert response.status_code == 500
        assert "error" in response.get_json()

@patch('backend.app.client')
def test_get_stock_data_exception(mock_client):
    mock_client.get_dataframe.side_effect = Exception("API down")
    result = get_stock_data("FAKE")
    assert isinstance(result, dict)
    assert "error" in result

@patch('backend.app.client')
def test_get_stock_data_not_enough_data(mock_client):
    mock_data = MagicMock()
    mock_data.empty = False
    mock_data.len.return_value = 2  # Менше 5 записів
    mock_data.sort_index.return_value.head.return_value.iterrows.return_value = [
        (datetime(2024, 4, 15), {'close': 150}),
        (datetime(2024, 4, 14), {'close': 152}),
    ]
    mock_client.get_dataframe.return_value = mock_data

    result = get_stock_data("AAPL")
    assert isinstance(result, dict)
    assert "error" in result

@patch('backend.app.get_stock_data')
def test_get_stocks_default_tickers(mock_get_stock_data):
    mock_get_stock_data.return_value = [
        {"date": "2024-04-15", "close": 150},
        {"date": "2024-04-14", "close": 151},
        {"date": "2024-04-13", "close": 152},
        {"date": "2024-04-12", "close": 153},
        {"date": "2024-04-11", "close": 154},
        {"date": "2024-04-10", "close": 155},
    ]
    client = app.test_client()
    response = client.get('/api/stocks')

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0

def test_declined_last_3_days_not_enough_data():
    prices = [{"close": 90}]
    assert declined_last_3_days(prices) is True  # Технічно немає трьох елементів, all() над пустим True

def test_more_than_two_declines_in_last_5_days_not_enough_data():
    prices = [{"close": 90}]
    assert more_than_two_declines_in_last_5_days(prices) is False

