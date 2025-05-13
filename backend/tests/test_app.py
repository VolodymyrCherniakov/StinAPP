import json
import pytest
import requests
from datetime import datetime, timedelta
from threading import Thread
import pandas as pd
import tempfile
import logging
import os

# Importujeme aplikaci a sdílené proměnné/funkce
from backend.app import app, global_stock_cache, get_stock_entry, scheduled_stock_fetch, cache_lock, \
    declined_last_3_days, more_than_two_declines_in_last_5_days

# Vzorová data, která vrací naše náhradní (fake) funkce
FAKE_STOCK_DATA = {
    "company_name": "Test Company",
    "declined_last_3_days": False,
    "more_than_2_declines_last_5_days": False,
    "latest_close": 150.0,
    "history": [
        {"date": (datetime(2025, 5, 13) - timedelta(days=i)).strftime('%Y-%m-%d'), "close": 150.0 - i}
        for i in range(6)
    ]
}


@pytest.fixture(autouse=True)
def clear_cache():
    """Vyčistí globální cache před a po každém testu."""
    with cache_lock:
        global_stock_cache.clear()
    yield
    with cache_lock:
        global_stock_cache.clear()


@pytest.fixture
def client():
    """Vytvoří testovacího klienta pro Flask aplikaci."""
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def mock_tiingo_client(monkeypatch):
    """Mocks TiingoClient to prevent real API calls."""

    def fake_get_dataframe(ticker, *args, **kwargs):
        if ticker == "INVALID":
            raise requests.exceptions.HTTPError(
                response=FakeResponse({"detail": f"Error: Ticker '{ticker}' not found"}, 404))
        if ticker == "EMPTY":
            return pd.DataFrame()
        return pd.DataFrame({
            "close": [150.0 - i for i in range(6)],
            "date": [(datetime(2025, 5, 13) - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6)]
        })

    monkeypatch.setattr("backend.app.client.get_dataframe", fake_get_dataframe)


@pytest.fixture(autouse=True)
def mock_scheduler(monkeypatch):
    """Mocks the scheduler to prevent background tasks."""
    monkeypatch.setattr("backend.app.scheduler.start", lambda: None)
    monkeypatch.setattr("backend.app.scheduler.shutdown", lambda: None)


@pytest.fixture
def mock_get_stock_entry(monkeypatch):
    """Mocks get_stock_entry to return FAKE_STOCK_DATA."""

    def fake_get_stock_entry(ticker, use_cache_only=False, force_refresh=False):
        return FAKE_STOCK_DATA.copy()

    monkeypatch.setattr("backend.app.get_stock_entry", fake_get_stock_entry)
    return fake_get_stock_entry


def fake_get_stock_entry_error(ticker, use_cache_only=False, force_refresh=False):
    """Fake funkce, která simuluje chybu (např. ticker nenalezen)."""
    return {"error": f"Ticker '{ticker}' nebyl nalezen."}


class FakeResponse:
    def __init__(self, json_data, status_code):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("Fake error")


# ------------------------- Testy endpointů -------------------------

def test_hello_endpoint(client):
    """Testuje GET /api/hello."""
    response = client.get('/api/hello')
    data = response.get_json()
    assert response.status_code == 200
    assert data.get("message") == "Hello from Docker!"


def test_get_stocks_empty(client):
    """Ověří, že při GET /api/stocks je cache prázdná."""
    response = client.get('/api/stocks')
    data = response.get_json()
    assert response.status_code == 200
    assert data == {}


def test_add_and_check_success(client, mock_get_stock_entry):
    """Test endpointu /api/stocks/add_and_check pro platný ticker."""
    response = client.post('/api/stocks/add_and_check', json={"ticker": "AAPL"})
    data = response.get_json()
    assert response.status_code == 200
    # Ověříme, že ticker je klíč v odpovědi a data odpovídají našim fake datům
    assert "AAPL" in data
    assert data["AAPL"]["company_name"] == FAKE_STOCK_DATA["company_name"]


def test_add_and_check_missing_ticker(client):
    """Pokud není ticker zadán, očekává se error."""
    response = client.post('/api/stocks/add_and_check', json={})
    data = response.get_json()
    assert response.status_code == 400
    assert "error" in data


def test_remove_ticker_success(client):
    """Nejprve vložíme ticker do cache, poté ověříme jeho odebrání."""
    with cache_lock:
        global_stock_cache["MSFT"] = FAKE_STOCK_DATA.copy()
    response = client.post('/api/stocks/remove', json={"ticker": "msft"})
    data = response.get_json()
    assert response.status_code == 200
    assert data.get("removed") == "MSFT"

    # Znovu odebrání už neexistujícího tickeru
    response = client.post('/api/stocks/remove', json={"ticker": "MSFT"})
    data = response.get_json()
    assert response.status_code == 404
    assert "error" in data


def test_send_recommendations_success(client, monkeypatch):
    """Test endpointu /api/stocks/recommend při úspěšném odeslání."""
    with cache_lock:
        global_stock_cache["TSLA"] = FAKE_STOCK_DATA.copy()

    def fake_requests_post(url, json):
        return FakeResponse({}, 200)

    monkeypatch.setattr(requests, "post", fake_requests_post)
    response = client.post('/api/stocks/recommend')
    data = response.get_json()
    assert response.status_code == 200
    assert "TSLA" in data.get("odeslano", [])
    # Cache má jeden ticker, ověříme číslo
    assert data.get("celkem_v_cache") == 1


def test_send_recommendations_failure(client, monkeypatch):
    """Simuluje selhání při volání externího API v /api/stocks/recommend."""
    with cache_lock:
        global_stock_cache["TSLA"] = FAKE_STOCK_DATA.copy()

    def fake_requests_post_fail(url, json):
        raise Exception("Simulovaná chyba")

    monkeypatch.setattr(requests, "post", fake_requests_post_fail)
    response = client.post('/api/stocks/recommend')
    data = response.get_json()
    assert response.status_code == 500
    assert "error" in data


def test_fetch_and_filter_news_success(client, monkeypatch):
    """Test endpointu /api/news s fake news daty."""
    fake_news = [
        {"name": "News1", "date": "2025-05-12", "rating": 5},
        {"name": "News2", "date": "2025-05-11", "rating": 2},
        {"name": "News3", "date": "2025-05-10", "rating": 8}
    ]

    def fake_requests_get(url):
        return FakeResponse(fake_news, 200)

    monkeypatch.setattr(requests, "get", fake_requests_get)
    response = client.post('/api/news', json={"api_url": "http://fakeapi/news", "min_rating_for_sell": 4})
    data = response.get_json()
    assert response.status_code == 200
    assert "data" in data
    # Ověříme, že zprávy s ratingem nižším než 4 mají nastavené sell = 1
    for item in data["data"]:
        if item["rating"] < 4:
            assert item["sell"] == 1
        else:
            assert item["sell"] == 0


def test_fetch_and_filter_news_missing_api_url(client):
    """Pokud v těle požadavku chybí api_url, vrátí se error."""
    response = client.post('/api/news', json={"min_rating_for_sell": 4})
    data = response.get_json()
    assert response.status_code == 400
    assert "error" in data


def test_scheduled_stock_fetch(monkeypatch):
    """Simuluje aktualizaci stocků v cache voláním scheduled_stock_fetch."""
    with cache_lock:
        global_stock_cache["IBM"] = {"company_name": "Old Value"}

    def fake_get_stock_entry_for_schedule(ticker, use_cache_only=False, force_refresh=False):
        return FAKE_STOCK_DATA.copy()

    monkeypatch.setattr("backend.app.get_stock_entry", fake_get_stock_entry_for_schedule)
    scheduled_stock_fetch()
    # Ověříme, že data v cache byla aktualizována
    assert global_stock_cache.get("IBM") == FAKE_STOCK_DATA


def test_error_handler(client, monkeypatch):
    """
    Simuluje neodchycenou výjimku v rámci endpointu /api/stocks/add_and_check
    nahrazením funkce get_stock_entry tak, aby vyvolala výjimku.
    """
    monkeypatch.setattr("backend.app.get_stock_entry",
                        lambda ticker, use_cache_only=False, force_refresh=False: (_ for _ in ()).throw(
                            ValueError("Test error")))
    response = client.post('/api/stocks/add_and_check', json={"ticker": "ERROR"})
    data = response.get_json()
    assert response.status_code == 500
    assert "error" in data


def test_declined_last_3_days_true():
    # Tři po sobě jdoucí poklesy (nejnovější: 93 > 92 > 91)
    prices = [
        {"date": "2025-05-10", "close": 93},
        {"date": "2025-05-09", "close": 92},
        {"date": "2025-05-08", "close": 91},
        {"date": "2025-05-07", "close": 90}
    ]
    assert declined_last_3_days(prices) is True


def test_declined_last_3_days_false():
    # Rostoucí ceny
    prices = [
        {"date": "2025-05-10", "close": 90},
        {"date": "2025-05-09", "close": 91},
        {"date": "2025-05-08", "close": 92}
    ]
    assert declined_last_3_days(prices) is False


def test_declined_last_3_days_insufficient_data():
    # Méně než 3 dny
    prices = [
        {"date": "2025-05-10", "close": 90},
        {"date": "2025-05-09", "close": 91}
    ]
    assert declined_last_3_days(prices) is False


def test_more_than_two_declines_in_last_5_days_true():
    # Tři poklesy (nejnovější: 95 > 94 > 92 > 91)
    prices = [
        {"date": "2025-05-10", "close": 95},
        {"date": "2025-05-09", "close": 94},
        {"date": "2025-05-08", "close": 92},
        {"date": "2025-05-07", "close": 91},
        {"date": "2025-05-06", "close": 93},
        {"date": "2025-05-05", "close": 96}
    ]
    assert more_than_two_declines_in_last_5_days(prices) is True


def test_more_than_two_declines_in_last_5_days_false():
    # Jen dva poklesy
    prices = [
        {"date": "2025-05-10", "close": 95},
        {"date": "2025-05-09", "close": 94},
        {"date": "2025-05-08", "close": 93},
        {"date": "2025-05-07", "close": 94},
        {"date": "2025-05-06", "close": 95},
        {"date": "2025-05-05", "close": 96}
    ]
    assert more_than_two_declines_in_last_5_days(prices) is False


def test_more_than_two_declines_in_last_5_days_insufficient_data():
    # Méně než 6 dní
    prices = [
        {"date": "2025-05-10", "close": 95},
        {"date": "2025-05-09", "close": 94},
        {"date": "2025-05-08", "close": 93},
        {"date": "2025-05-07", "close": 92}
    ]
    assert more_than_two_declines_in_last_5_days(prices) is False


def test_logs_download(client):
    """Ověří, že endpoint pro stažení logu vrací soubor."""
    response = client.get("/api/logs/download")
    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith("attachment")


def test_handle_exception(client):
    """Volání neexistující cesty vyvolá 500 a error se zaloguje."""
    response = client.get("/api/neexistuje")
    assert response.status_code == 500
    assert "error" in response.get_json()


def test_get_stock_entry_insufficient_data(monkeypatch):
    """Testuje get_stock_entry při nedostatečném množství dat."""

    def fake_get_dataframe(ticker, *args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr("backend.app.client.get_dataframe", fake_get_dataframe)
    response = get_stock_entry("EMPTY")
    assert "error" in response
    assert response["error"] == "Nedostatek dat pro EMPTY"


def test_get_stock_entry_404_error(monkeypatch):
    """Testuje get_stock_entry při HTTP 404 chybě (ticker nenalezen)."""

    def fake_get_dataframe(ticker, *args, **kwargs):
        raise requests.exceptions.HTTPError(
            response=FakeResponse({"detail": f"Error: Ticker '{ticker}' not found"}, 404))

    monkeypatch.setattr("backend.app.client.get_dataframe", fake_get_dataframe)
    response = get_stock_entry("INVALID")
    assert "error" in response
    assert response["error"] == "Ticker 'INVALID' nebyl nalezen."


def test_get_stock_entry_cache_only_missing(client, monkeypatch):
    """Testuje get_stock_entry s use_cache_only=True a chybějícím tickerem."""
    response = get_stock_entry("AAPL", use_cache_only=True)
    assert "error" in response
    assert response["error"] == "Data pro AAPL nejsou v cache."


def test_get_stock_entry_force_refresh(client, mock_get_stock_entry):
    """Testuje get_stock_entry s force_refresh=True."""
    with cache_lock:
        global_stock_cache["AAPL"] = {"company_name": "Old Company"}

    response = get_stock_entry("AAPL", force_refresh=True)
    assert response["company_name"] == FAKE_STOCK_DATA["company_name"]
    assert response != {"company_name": "Old Company"}


def test_add_and_check_invalid_ticker(client, monkeypatch):
    """Testuje /api/stocks/add_and_check s neplatným tickerem."""
    monkeypatch.setattr("backend.app.get_stock_entry", fake_get_stock_entry_error)
    response = client.post('/api/stocks/add_and_check', json={"ticker": "INVALID"})
    data = response.get_json()
    assert response.status_code == 400
    assert "error" in data
    assert data["error"] == "Ticker 'INVALID' nebyl nalezen."


def test_send_recommendations_empty_filtered(client, monkeypatch):
    """Testuje /api/stocks/recommend, když žádné akcie nesplňují kritéria."""
    with cache_lock:
        global_stock_cache["TSLA"] = {
            **FAKE_STOCK_DATA,
            "declined_last_3_days": True  # Nesplňuje podmínky
        }

    def fake_requests_post(url, json):
        return FakeResponse({}, 200)

    monkeypatch.setattr(requests, "post", fake_requests_post)
    response = client.post('/api/stocks/recommend')
    data = response.get_json()
    assert response.status_code == 200
    assert data["odeslano"] == []
    assert data["celkem_v_cache"] == 1


def test_fetch_and_filter_news_api_failure(client, monkeypatch):
    """Testuje /api/news při selhání externího API."""

    def fake_requests_get(url):
        return FakeResponse({}, 500)

    monkeypatch.setattr(requests, "get", fake_requests_get)
    response = client.post('/api/news', json={"api_url": "http://fakeapi/news", "min_rating_for_sell": 4})
    data = response.get_json()
    assert response.status_code == 500
    assert "error" in data
    assert data["error"] == "Nepodařilo se stáhnout data ze zadané adresy"


def test_logging(client, monkeypatch):
    """Testuje, zda log_request a log_response zapisují do logu."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_log:
        monkeypatch.setattr("backend.app.log_file", temp_log.name)
        monkeypatch.setattr("backend.app.logging.basicConfig", lambda **kwargs: None)
        logger = logging.getLogger("backend.app")
        handler = logging.FileHandler(temp_log.name)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        response = client.get('/api/hello')
        assert response.status_code == 200

        with open(temp_log.name, 'r') as log_file:
            log_content = log_file.read()
            assert "[REQUEST] GET /api/hello" in log_content
            assert "[RESPONSE] GET /api/hello" in log_content
            assert "Status: 200" in log_content

        handler.close()
    os.unlink(temp_log.name)


def test_cache_lock_concurrent_access(monkeypatch, mock_get_stock_entry):
    """Testuje bezpečnost cache při souběžném přístupu."""

    def add_ticker(ticker):
        get_stock_entry(ticker)

    threads = [Thread(target=add_ticker, args=(f"TEST{i}",)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with cache_lock:
        assert len(global_stock_cache) == 5
        for i in range(5):
            assert global_stock_cache[f"TEST{i}"] == FAKE_STOCK_DATA


def test_api_key_loading(monkeypatch):
    """Testuje načítání API klíče."""
    monkeypatch.setattr("os.getenv", lambda key, default=None: "fake-key" if key == "API_KEY" else default)
    monkeypatch.setattr("backend.app.load_dotenv", lambda: None)
    from importlib import reload
    import backend.app
    reload(backend.app)  # Reload module to apply mocked environment
    assert backend.app.API_KEY == "fake-key"