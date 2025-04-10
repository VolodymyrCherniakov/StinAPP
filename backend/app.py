from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
from tiingo import TiingoClient
from datetime import datetime, timedelta

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv('API_KEY')

# Configure Tiingo client
config = {
    'api_key': API_KEY,
    'session': True
}
client = TiingoClient(config)

app = Flask(__name__)
CORS(app)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
    'META', 'NVDA', 'JPM', 'V', 'WMT',
    'DIS', 'NFLX', 'PYPL', 'KO', 'PEP'
]

def declined_last_3_days(prices):
    return all(prices[i]['close'] < prices[i + 1]['close'] for i in range(3))

def more_than_two_declines_in_last_5_days(prices):
    return sum(prices[i]['close'] < prices[i + 1]['close'] for i in range(5)) > 2

def get_stock_data(ticker):
    try:
        # Získáme data za posledních 6 dní (potřebujeme 5 rozdílů)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=10)

        historical_prices = client.get_dataframe(
            ticker,
            startDate=start_date.strftime('%Y-%m-%d'),
            endDate=end_date.strftime('%Y-%m-%d')
        )

        if historical_prices.empty or len(historical_prices) < 5:
            return {"error": f"Nedostatek dat pro {ticker}"}

        # Posledních 5 záznamů, seřazených od nejnovějšího
        latest_data = historical_prices.sort_index(ascending=False).head(6)

        # Převod na list dictů pro jednodušší práci dál
        prices = [
            {"date": date.strftime('%Y-%m-%d'), "close": row['close']}
            for date, row in latest_data.iterrows()
        ]

        return prices

    except Exception as e:
        logger.error(f"Chyba při načítání {ticker}: {e}")
        return {"error": str(e)}

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    tickers = request.args.getlist('tickers') or DEFAULT_TICKERS
    results = {}

    for ticker in tickers:
        stock_data = get_stock_data(ticker)

        if isinstance(stock_data, dict) and "error" in stock_data:
            results[ticker] = stock_data
            continue

        try:
            declined3 = bool(declined_last_3_days(stock_data))
            declines5 = bool(more_than_two_declines_in_last_5_days(stock_data))
        except Exception as e:
            logger.warning(f"Chyba při výpočtu pro {ticker}: {e}")
            results[ticker] = {"error": "Nelze vyhodnotit trend."}
            continue

        results[ticker] = {
            "declined_last_3_days": declined3,
            "more_than_2_declines_last_5_days": declines5,
            "latest_close": float(stock_data[0]['close']),
            "history": stock_data
        }

    return jsonify(results)


@app.route('/api/hello', methods=['GET'])
def hello_world():
    app.logger.info("Hello endpoint called")
    return jsonify({"message": "Hello from Docker!"})

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Nezachycená výjimka: {e}")
    return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
