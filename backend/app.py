import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
from tiingo import TiingoClient
from datetime import datetime, timedelta
from threading import Lock
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Load API key
load_dotenv()
API_KEY = os.getenv('API_KEY')

# Configure Tiingo
client = TiingoClient({'api_key': API_KEY, 'session': True})

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKER_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com, Inc.",
    "TSLA": "Tesla, Inc.",
    "META": "Meta Platforms, Inc.",
    "NVDA": "NVIDIA Corporation",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "WMT": "Walmart Inc.",
    "DIS": "The Walt Disney Company",
    "NFLX": "Netflix, Inc.",
    "PYPL": "PayPal Holdings, Inc.",
    "KO": "The Coca-Cola Company",
    "PEP": "PepsiCo, Inc.",
    "INTC": "Intel Corporation",
    "CSCO": "Cisco Systems, Inc.",
    "ORCL": "Oracle Corporation",
    "CRM": "Salesforce, Inc.",
    "BA": "The Boeing Company",
    "NKE": "Nike, Inc.",
    "COST": "Costco Wholesale Corporation",
    "ABNB": "Airbnb, Inc.",
    "ADBE": "Adobe Inc.",
    "AMD": "Advanced Micro Devices, Inc.",
    "GE": "General Electric Company",
    "T": "AT&T Inc.",
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "WFC": "Wells Fargo & Company",
    "BAC": "Bank of America Corporation",
    "GS": "The Goldman Sachs Group, Inc.",
    "LMT": "Lockheed Martin Corporation",
    "CAT": "Caterpillar Inc.",
    "IBM": "International Business Machines Corporation",
    "MCD": "McDonald's Corporation",
    "MMM": "3M Company",
    "AXP": "American Express Company",
    "HON": "Honeywell International Inc.",
    "SBUX": "Starbucks Corporation",
    "GM": "General Motors Company",
    "F": "Ford Motor Company",
    "PFE": "Pfizer Inc.",
    "JNJ": "Johnson & Johnson",
    "MRK": "Merck & Co., Inc.",
    "TMO": "Thermo Fisher Scientific Inc.",
    "LLY": "Eli Lilly and Company",
    "UNH": "UnitedHealth Group Incorporated",
    "BMY": "Bristol-Myers Squibb Company"
}

global_stock_cache = {}
cache_lock = Lock()

def declined_last_3_days(prices):
    return bool(all(prices[i]['close'] < prices[i + 1]['close'] for i in range(3)))

def more_than_two_declines_in_last_5_days(prices):
    return bool(sum(prices[i]['close'] < prices[i + 1]['close'] for i in range(5)) > 2)

def get_stock_entry(ticker, use_cache_only=False, force_refresh=False):
    with cache_lock:
        if ticker in global_stock_cache and not force_refresh:
            return global_stock_cache[ticker]
        elif use_cache_only:
            return {"error": f"Data pro {ticker} nejsou v cache."}

    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=10)
        historical_prices = client.get_dataframe(ticker, startDate=start_date.strftime('%Y-%m-%d'), endDate=end_date.strftime('%Y-%m-%d'))

        if historical_prices.empty or len(historical_prices) < 5:
            return {"error": f"Nedostatek dat pro {ticker}"}

        latest_data = historical_prices.sort_index(ascending=False).head(6)
        prices = [{"date": date.strftime('%Y-%m-%d'), "close": row['close']} for date, row in latest_data.iterrows()]

        result_entry = {
            "company_name": TICKER_NAMES.get(ticker, 'Neznámá společnost'),
            "declined_last_3_days": declined_last_3_days(prices),
            "more_than_2_declines_last_5_days": more_than_two_declines_in_last_5_days(prices),
            "latest_close": float(prices[0]['close']),
            "history": prices
        }

        with cache_lock:
            global_stock_cache[ticker] = result_entry

        return result_entry

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            return {"error": f"Ticker '{ticker}' nebyl nalezen."}
        return {"error": f"HTTP chyba: {str(http_err)}"}
    except Exception as e:
        logger.error(f"Chyba při načítání {ticker}: {e}")
        return {"error": "Nastala chyba při získávání dat."}

def scheduled_stock_fetch():
    logger.info("Spouštím aktualizaci tickerů v cache...")
    with cache_lock:
        tickers_to_update = list(global_stock_cache.keys())

    for ticker in tickers_to_update:
        try:
            updated_entry = get_stock_entry(ticker, force_refresh=True)
            with cache_lock:
                global_stock_cache[ticker] = updated_entry
            logger.info(f"Aktualizován: {ticker}")
        except Exception as e:
            logger.warning(f"Chyba při aktualizaci {ticker}: {e}")


@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    with cache_lock:
        return jsonify(global_stock_cache)

@app.route('/api/stocks/add_and_check', methods=['POST'])
def add_and_check_ticker():
    data = request.get_json()
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Ticker není zadán"}), 400

    entry = get_stock_entry(ticker)
    if "error" in entry:
        return jsonify({"error": entry["error"]}), 400

    with cache_lock:
        global_stock_cache[ticker] = entry

    return jsonify({ticker: entry})

@app.route('/api/stocks/remove', methods=['POST'])
def remove_ticker():
    data = request.get_json()
    ticker = data.get("ticker", "").upper()

    if not ticker:
        return jsonify({"error": "Ticker není zadán"}), 400

    with cache_lock:
        if ticker in global_stock_cache:
            del global_stock_cache[ticker]
            return jsonify({"removed": ticker}), 200
        else:
            return jsonify({"error": "Ticker nebyl nalezen v cache"}), 404




@app.route('/api/stocks/recommend', methods=['POST'])
def send_recommendations():
    with cache_lock:
        filtered = {
            ticker: entry for ticker, entry in global_stock_cache.items()
            if not entry.get("declined_last_3_days") and not entry.get("more_than_2_declines_last_5_days")
        }

    if filtered:
        try:
            response = requests.post("https://news-production-257a.up.railway.app/recommendations", json=filtered)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Chyba při odesílání doporučení: {e}")
            return jsonify({"error": "Nepodařilo se odeslat doporučení"}), 500

    return jsonify({
        "odeslano": list(filtered.keys()),
        "celkem_v_cache": len(global_stock_cache)
    })

@app.route('/api/news', methods=['POST'])
def process_news():
    try:
        data = request.get_json()
        api_url = data.get("api_url")
        min_rating_for_sell = int(data.get("min_rating_for_sell", -5))

        if not api_url:
            return jsonify({"error": "Chybí api_url"}), 400

        # 1. Získání dat ze zadaného API (např. /news)
        news_response = requests.get(api_url)
        news_response.raise_for_status()
        news_data = news_response.json()

        if not isinstance(news_data, list):
            return jsonify({"error": "Zprávy musí být seznam"}), 400

        # 2. Zpracování dat a výpočet sell
        processed = []
        for item in news_data:
            try:
                name = item.get("name")
                date = item.get("date")
                rating = int(item.get("rating"))

                if name is None or date is None:
                    continue

                sell = 1 if rating <= min_rating_for_sell else 0

                processed.append({
                    "name": name,
                    "date": date,
                    "rating": rating,
                    "sell": sell
                })
            except Exception as e:
                logger.warning(f"Chyba při zpracování položky: {e}")
                continue

        # 3. Odeslání výsledku zpět do systému zpráv
        recommend_url = "https://news-production-257a.up.railway.app/recommend-sell"
        response = requests.post(recommend_url, json=processed)
        response.raise_for_status()

        return jsonify({
            "odeslano_na": recommend_url,
            "pocet": len(processed),
            "data": processed
        })

    except requests.exceptions.RequestException as re:
        logger.error(f"Chyba při komunikaci s API: {re}")
        return jsonify({"error": "Nelze kontaktovat vzdálené API"}), 500
    except Exception as e:
        logger.error(f"Chyba v /api/news/: {e}")
        return jsonify({"error": "Interní chyba serveru"}), 500



@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify({"message": "Hello from Docker!"})

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Nezachycená výjimka: {e}")
    return jsonify(error=str(e)), 500

# Scheduler pro obnoveni dat
scheduler = BackgroundScheduler()
trigger = CronTrigger(hour='0,6,12,18', minute=0)
scheduler.add_job(func=scheduled_stock_fetch, trigger=trigger)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)