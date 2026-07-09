import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import httpx


class ExchangeError(Exception):
    pass


class BinanceClient:
    """Bare minimum Binance Spot API wrapper for placing market orders and checking balance."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.binance.com"):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=15.0)

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(self.api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()

    def _headers(self) -> Dict[str, str]:
        return {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "dca-scheduler/0.1",
        }

    def get_server_time(self) -> int:
        r = self._client.get(f"{self.base_url}/api/v3/time")
        r.raise_for_status()
        return r.json()["serverTime"]

    def get_asset_balance(self, asset: str) -> float:
        params = {"timestamp": int(time.time() * 1000)}
        params["signature"] = self._sign(params)
        resp = self._client.get(
            f"{self.base_url}/api/v3/account",
            params=params,
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise ExchangeError(f"Failed to fetch balance: {resp.text}")

        data = resp.json()
        for b in data.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def buy_market(self, symbol: str, quote_quantity: float) -> Dict[str, Any]:
        # Binance allows quoteOrderQty for market buys (spend exact amount of USDT/EUR)
        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": f"{quote_quantity:.2f}",
            "timestamp": int(time.time() * 1000),
        }
        params["signature"] = self._sign(params)

        resp = self._client.post(
            f"{self.base_url}/api/v3/order",
            params=params,
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise ExchangeError(f"Order failed: {resp.status_code} {resp.text}")

        return resp.json()
