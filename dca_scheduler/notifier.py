import json
import logging
import urllib.error
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)


class Notifier:
    """Sends execution alerts via ntfy topic or generic json webhooks."""

    def __init__(self, ntfy_url: Optional[str] = None, webhook_url: Optional[str] = None):
        self.ntfy_url = ntfy_url.rstrip("/") if ntfy_url else None
        self.webhook_url = webhook_url

    def notify_order_filled(self, pair: str, spent: float, received: float, fee: float, tx_id: str):
        msg = f"DCA buy filled: {spent:.2f} -> {received:.6f} {pair} (fee: {fee:.4f}, id: {tx_id[:8]})"
        self._send(title="DCA Order Success", body=msg, tags=["white_check_mark", "moneybag"])

    def notify_failure(self, pair: str, error: str):
        msg = f"DCA order for {pair} failed: {error}"
        self._send(title="DCA Order Failed", body=msg, tags=["x", "warning"], priority="high")

    def _send(self, title: str, body: str, tags: list[str] = None, priority: str = "default"):
        if self.ntfy_url:
            self._send_ntfy(title, body, tags or [], priority)
        if self.webhook_url:
            self._send_webhook(title, body)

    def _send_ntfy(self, title: str, body: str, tags: list[str], priority: str):
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": ",".join(tags),
            "Content-Type": "text/plain; charset=utf-8",
        }
        req = urllib.request.Request(
            self.ntfy_url,
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 300:
                    log.warning("ntfy returned status %d", resp.status)
        except urllib.error.URLError as e:
            log.warning("failed to send ntfy alert: %s", e)

    def _send_webhook(self, title: str, body: str):
        payload = json.dumps({"title": title, "text": body}).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 300:
                    log.warning("webhook returned status %d", resp.status)
        except urllib.error.URLError as e:
            log.warning("failed to dispatch webhook: %s", e)
