import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    BLOB_BACKEND = os.environ.get('BLOB_BACKEND', 'disk')
    BLOB_STORE_PATH = os.environ.get('BLOB_STORE_PATH', '/tmp/marketbard')
    TRADE_BLOB_STORE_PATH = os.environ.get('TRADE_BLOB_STORE_PATH', '/tmp/markettrade')
    PORTFOLIO_STATE_PATH = os.environ.get('PORTFOLIO_STATE_PATH', '/tmp/markettrade/portfolio_state.json')
    PORTFOLIO_POLL_INTERVAL = float(os.environ.get('PORTFOLIO_POLL_INTERVAL', '2.0'))
    BLOB_SERVER_PORT = int(os.environ.get('BLOB_SERVER_PORT', '5001'))

    def __str__(self):
        return (f"Backend: {self.BLOB_BACKEND}\n"
                f"Store path: {self.BLOB_STORE_PATH}\n"
                f"Portfolio state: {self.PORTFOLIO_STATE_PATH}\n"
                f"Port: {self.BLOB_SERVER_PORT}")
