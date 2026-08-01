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
    BLOB_SERVER_PORT = int(os.environ.get('BLOB_SERVER_PORT', '5001'))

    def __str__(self):
        return (f"Backend: {self.BLOB_BACKEND}\n"
                f"Store path: {self.BLOB_STORE_PATH}\n"
                f"Port: {self.BLOB_SERVER_PORT}")
