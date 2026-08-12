import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
import httpx

log = logging.getLogger("dca_scheduler.exchange")


class ExchangeError(Exception):
    pass


class BinanceClient:
    """Bare minimum Binance Spot API wrapper for placing market orders and checking balance."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.binance.com"):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=15.0)
        self._time_offset = 0

    def sync_time(self):
        # local clock drift can cause recvWindow rejections
        r = self._client.get(f"{self.base_url}/api/v3/time")
        r.raise_for_status()
        server_time = r.json()["serverTime"]
        local_time = int(time.time() * 1000)
        self._time_offset = server_time - local_time

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(self.api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()

    def _headers(self) -> Dict[str, str]:
        return {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "dca-scheduler/0.1",
        }

    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> httpx.Response:
        params = kwargs.pop("params", {}) or {}
        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = 5000
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        headers = self._headers()

        for attempt in range(3):
            try:
                resp = self._client.request(method, url, params=params, headers=headers, **kwargs)
                # print(f"DEBUG: {resp.status_code} {resp.text}")
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2 * (attempt + 1)))
                    log.warning(f"Rate limited (429), sleeping {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                return resp
            except httpx.NetworkError as exc:
                if attempt == 2:
                    raise ExchangeError(f"Network error after 3 attempts: {exc}") from exc
                time.sleep(1.0 * (attempt + 1))

        raise ExchangeError(f"Failed request {method} {endpoint} after retries")

    def get_asset_balance(self, asset: str) -> float:
        resp = self._request("GET", "/api/v3/account", signed=True)
        if resp.status_code != 200:
            raise ExchangeError(f"Failed to fetch balance: {resp.text}")

        data = resp.json()
        for b in data.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def buy_market(self, symbol: str, quote_quantity: float, precision: int = 2) -> Dict[str, Any]:
        # TODO: read quote precision from exchangeInfo endpoint dynamically
        fmt = f"{{:.{precision}f}}"
        params = {
            "symbol": symbol.upper(),
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": fmt.format(quote_quantity),
            "newOrderRespType": "FULL",
        }
        resp = self._request("POST", "/api/v3/order", signed=True, params=params)
        if resp.status_code != 200:
            raise ExchangeError(f"Order failed ({resp.status_code}): {resp.text}")

        payload = resp.json()
        return payload

    @staticmethod
    def parse_execution_summary(order_payload: Dict[str, Any]) -> Tuple[float, float, float]:
        """Extracts (executed_qty, cummulative_quote_qty, fee) from FULL order response."""
        fills: List[Dict[str, Any]] = order_payload.get("fills", [])
        exec_qty = float(order_payload.get("executedQty", 0.0))
        cum_quote = float(order_payload.get("cummulativeQuoteQty", 0.0))
        total_fee = sum(float(f.get("commission", 0.0)) for f in fills)
        return exec_qty, cum_quote, total_fee
