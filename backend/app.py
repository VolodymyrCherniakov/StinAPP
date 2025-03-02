from flask import Flask, jsonify
from flask_cors import CORS
import os
# from logging_config import configure_logging
import logging

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes
# configure_logging()
logger = logging.getLogger(__name__)

@app.route('/api/hello', methods=['GET'])
def hello_world():
    app.logger.info("HelloWorld endpoint was called")
    return jsonify({"message": "Hello from Docker!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)