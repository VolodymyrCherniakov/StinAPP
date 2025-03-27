from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv('API_KEY')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
logger = logging.getLogger(__name__)

# Alpha Vantage API URL
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

# Seznam 20 populárních tickerů jako výchozí hodnota
DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
    'META', 'NVDA', 'JPM', 'V', 'WMT',
    'DIS', 'NFLX', 'PYPL', 'KO', 'PEP',
    'INTC', 'AMD', 'CSCO', 'IBM', 'ORCL'
]

def declined_last_3_days(time_series, dates):
    """Check if the stock declined in the last 3 days"""
    return all(
        float(time_series[dates[i]]['4. close']) < float(time_series[dates[i + 1]]['4. close'])
        for i in range(3)
    )

def more_than_two_declines_in_last_5_days(time_series, dates):
    """Check if the stock had more than two declines in the last 5 days"""
    return sum(
        float(time_series[dates[i]]['4. close']) < float(time_series[dates[i + 1]]['4. close'])
        for i in range(5)
    ) > 2

def get_stock_data(ticker):
    """Retrieve stock data from Alpha Vantage API"""
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': ticker,
        'apikey': API_KEY
    }
    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if 'Time Series (Daily)' in data:
            return data['Time Series (Daily)']
        else:
            logger.warning(f"No data available for ticker: {ticker}")
            return {"error": f"Data nejsou dostupná pro ticker {ticker}."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
        return {"error": "Nepodařilo se získat data."}

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """Retrieve data for user-defined or default stock tickers"""
    tickers = request.args.getlist('tickers')  # Get list of tickers from query params
    if not tickers:
        # Použij výchozí seznam 20 tickerů, pokud nejsou zadány žádné
        tickers = DEFAULT_TICKERS
        logger.info("No tickers provided, using default list of 20 tickers")

    stock_data = {}
    for ticker in tickers:
        stock_data[ticker] = get_stock_data(ticker)

    return jsonify(stock_data)

@app.route('/api/hello', methods=['GET'])
def hello_world():
    """Simple hello endpoint for testing"""
    app.logger.info("HelloWorld endpoint was called")
    return jsonify({"message": "Hello from Docker!"})

if __name__ == '__main__':
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=8000)