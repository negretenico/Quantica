from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Empty, PriorityQueue
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Position:
    quantity: float
    avg_entry_price: float
    opened_at: str


class Portfolio:
    def __init__(self, cash: float, starting_balance: float):
        self.cash = cash
        self.starting_balance = starting_balance
        self.positions: dict[str, Position] = {}
        self.realized_pnl: float = 0.0
        self.updated_at: str = datetime.now(timezone.utc).isoformat()
        self._lock = threading.Lock()

    def record_buy(self, symbol: str, entry_price: float, sized_quantity: float) -> None:
        with self._lock:
            cost = entry_price * sized_quantity
            self.cash -= cost
            existing = self.positions.get(symbol)
            if existing is not None:
                total_qty = existing.quantity + sized_quantity
                weighted_avg = (
                    (existing.avg_entry_price * existing.quantity + entry_price * sized_quantity)
                    / total_qty
                )
                existing.quantity = total_qty
                existing.avg_entry_price = weighted_avg
            else:
                self.positions[symbol] = Position(
                    quantity=sized_quantity,
                    avg_entry_price=entry_price,
                    opened_at=datetime.now(timezone.utc).isoformat(),
                )
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_sell(self, symbol: str, exit_price: float, sized_quantity: float) -> None:
        with self._lock:
            pos = self.positions.get(symbol)
            if pos is None:
                return
            sell_qty = min(sized_quantity, pos.quantity)
            self.cash += exit_price * sell_qty
            self.realized_pnl += (exit_price - pos.avg_entry_price) * sell_qty
            pos.quantity -= sell_qty
            if pos.quantity <= 1e-12:
                del self.positions[symbol]
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def close_position(self, symbol: str, current_price: float) -> None:
        with self._lock:
            pos = self.positions.get(symbol)
            if pos is None:
                return
            self.cash += current_price * pos.quantity
            self.realized_pnl += (current_price - pos.avg_entry_price) * pos.quantity
            del self.positions[symbol]
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def has_position(self, symbol: str) -> bool:
        with self._lock:
            return symbol in self.positions

    def get_position(self, symbol: str) -> Position | None:
        with self._lock:
            return self.positions.get(symbol)

    def total_value(self, price_fn: Callable[[str], float]) -> float:
        with self._lock:
            position_value = sum(
                price_fn(sym) * pos.quantity
                for sym, pos in self.positions.items()
            )
            return self.cash + position_value

    def unrealized_pnl(self, price_fn: Callable[[str], float]) -> float:
        with self._lock:
            return sum(
                (price_fn(sym) - pos.avg_entry_price) * pos.quantity
                for sym, pos in self.positions.items()
            )

    def portfolio_pnl(self, price_fn: Callable[[str], float]) -> float:
        return self.realized_pnl + self.unrealized_pnl(price_fn)

    def save(self, path: str) -> None:
        data = {
            "cash": self.cash,
            "starting_balance": self.starting_balance,
            "positions": {
                sym: {
                    "quantity": pos.quantity,
                    "avg_entry_price": pos.avg_entry_price,
                    "opened_at": pos.opened_at,
                }
                for sym, pos in self.positions.items()
            },
            "realized_pnl": self.realized_pnl,
            "updated_at": self.updated_at,
        }
        dir_path = os.path.dirname(path) or "."
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: str, starting_balance: float) -> Portfolio:
        try:
            with open(path) as f:
                data = json.load(f)
            portfolio = cls(
                cash=float(data["cash"]),
                starting_balance=float(data.get("starting_balance", starting_balance)),
            )
            portfolio.realized_pnl = float(data.get("realized_pnl", 0.0))
            portfolio.updated_at = data.get("updated_at", datetime.now(timezone.utc).isoformat())
            for sym, pos_data in data.get("positions", {}).items():
                portfolio.positions[sym] = Position(
                    quantity=float(pos_data["quantity"]),
                    avg_entry_price=float(pos_data["avg_entry_price"]),
                    opened_at=pos_data.get("opened_at", ""),
                )
            return portfolio
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.info("Portfolio state not loaded from %s (%s), starting fresh", path, exc)
            return cls(cash=starting_balance, starting_balance=starting_balance)


class PositionTimeoutScheduler:
    def __init__(
        self,
        portfolio: Portfolio,
        timeout_seconds: float,
        price_source: Callable[[str], float | None],
        on_close: Callable[[str, float], None],
    ):
        self._portfolio = portfolio
        self._timeout = timeout_seconds
        self._price_source = price_source
        self._on_close = on_close
        self._queue: PriorityQueue[tuple[float, str]] = PriorityQueue()
        self._cancelled: set[str] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("PositionTimeoutScheduler started (timeout=%.0fs)", timeout_seconds)

    def schedule(self, symbol: str) -> None:
        self._cancelled.discard(symbol)
        self._queue.put((time.time() + self._timeout, symbol))

    def cancel(self, symbol: str) -> None:
        self._cancelled.add(symbol)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                due_time, symbol = self._queue.get(timeout=5.0)
            except Empty:
                continue

            wait = due_time - time.time()
            if wait > 0:
                self._stop.wait(wait)
                if self._stop.is_set():
                    break

            if symbol in self._cancelled:
                self._cancelled.discard(symbol)
                continue

            if not self._portfolio.has_position(symbol):
                continue

            price = self._price_source(symbol)
            pos = self._portfolio.get_position(symbol)
            if price is None and pos is not None:
                price = pos.avg_entry_price
            if price is None:
                price = 0.0

            self._portfolio.close_position(symbol, price)
            logger.info("Position timeout — closed %s at %.4f", symbol, price)

            try:
                self._on_close(symbol, self._portfolio.realized_pnl)
            except Exception:
                logger.exception("on_close callback failed for %s", symbol)

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
