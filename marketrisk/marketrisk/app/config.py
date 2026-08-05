import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    MAX_TRADE_QUANTITY: float = float(os.environ.get('MAX_TRADE_QUANTITY', '1000.0'))
    MAX_SYMBOL_EXPOSURE: float = float(os.environ.get('MAX_SYMBOL_EXPOSURE', '5000.0'))
    MAX_DRAWDOWN_PCT: float = float(os.environ.get('MAX_DRAWDOWN_PCT', '0.20'))
    NEAR_LIMIT_THRESHOLD_PCT: float = float(os.environ.get('NEAR_LIMIT_THRESHOLD_PCT', '0.80'))
