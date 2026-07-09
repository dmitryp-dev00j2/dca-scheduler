import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quote_amount REAL NOT NULL,
    base_amount REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0.0,
    order_id TEXT UNIQUE,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_ts ON orders(timestamp);
"""


class OrderStore:
    def __init__(self, db_path: str = "dca.db"):
        self.db_path = str(Path(db_path).expanduser())
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(SCHEMA)

    def record_order(
        self,
        timestamp: int,
        symbol: str,
        side: str,
        quote_amount: float,
        base_amount: float,
        price: float,
        fee: float = 0.0,
        order_id: Optional[str] = None,
        status: str = "FILLED",
    ) -> int:
        query = """
        INSERT INTO orders (timestamp, symbol, side, quote_amount, base_amount, price, fee, order_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_conn() as conn:
            cur = conn.execute(
                query,
                (timestamp, symbol, side, quote_amount, base_amount, price, fee, order_id, status),
            )
            return cur.lastrowid

    def list_orders(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            if symbol:
                cur = conn.execute(
                    "SELECT * FROM orders WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                    (symbol.upper(), limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM orders ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
            return [dict(row) for row in cur.fetchall()]
