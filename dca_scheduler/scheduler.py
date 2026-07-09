import datetime
import logging
import random
import time
from typing import Optional

from dca_scheduler.exchange import ExchangeClient
from dca_scheduler.notifier import Notifier
from dca_scheduler.store import Store

logger = logging.getLogger("dca_scheduler.scheduler")


def compute_jitter(max_jitter_seconds: int) -> int:
    if max_jitter_seconds <= 0:
        return 0
    return random.randint(0, max_jitter_seconds)


class Scheduler:
    """Manages periodic DCA execution with randomized jitter delays."""

    def __init__(    
        self,
        pair: str,
        amount: float,
        interval_seconds: int,
        jitter_seconds: int = 300,
        store: Optional[Store] = None,
        exchange: Optional[ExchangeClient] = None,
        notifier: Optional[Notifier] = None,
        dry_run: bool = False,
    ):
        self.pair = pair.upper()
        self.target_amount = amount  # kept name from early prototype
        self.interval = interval_seconds
        self.jitter_sec = jitter_seconds
        self.store = store or Store()
        self.exchange = exchange or ExchangeClient()
        self.notifier = notifier
        self.dry_run = dry_run
        self._running = False

    def execute_tick(self) -> dict:
        scheduled_for = datetime.datetime.now(datetime.timezone.utc)
        logger.info("Executing buy order for %s (amount: %s)", self.pair, self.target_amount)

        if self.dry_run:
            logger.info("DRY RUN: skipping exchange order submission")
            res = {
                "order_id": "dry-run-" + str(int(scheduled_for.timestamp())),
                "pair": self.pair,
                "amount": self.target_amount,
                "filled_price": 0.0,
                "timestamp": scheduled_for.isoformat(),
                "is_dry_run": True,
            }
            self.store.record_order(res)
            return res

        try:
            order = self.exchange.market_buy(self.pair, self.target_amount)
            self.store.record_order(order)
            if self.notifier:
                self.notifier.notify_success(order)
            return order
        except Exception as e:
            logger.error("Order failed for %s: %s", self.pair, e)
            self.store.record_failure(self.pair, self.target_amount, str(e))
            if self.notifier:
                self.notifier.notify_failure(self.pair, self.target_amount, str(e))
            raise

    def run(self):
        self._running = True
        logger.info("Scheduler started for %s, interval=%ds, max_jitter=%ds", self.pair, self.interval, self.jitter_sec)

        while self._running:
            jitter = compute_jitter(self.jitter_sec)
            sleep_duration = self.interval + jitter
            next_run_ts = time.time() + sleep_duration
            next_run_dt = datetime.datetime.fromtimestamp(next_run_ts, tz=datetime.timezone.utc)

            logger.info("Next buy scheduled at %s (sleep %ds, jitter +%ds)", next_run_dt.strftime("%Y-%m-%d %H:%M:%S UTC"), sleep_duration, jitter)
            # print(f"[DEBUG] sleep_secs={sleep_duration} jitter={jitter}")

            # Sleep in 1s increments so SIGINT does not block until full interval expires
            while self._running and time.time() < next_run_ts:
                remaining = next_run_ts - time.time()
                time.sleep(min(remaining, 1.0))

            if not self._running:
                break

            # TODO: if system clock jumps backward by >1 hour (NTP sync/timezone change), reset next_tick
            try:
                self.execute_tick()
            except Exception:
                logger.warning("Tick failed, waiting for next scheduled interval")

    def stop(self):
        logger.info("Stopping scheduler...")
        self._running = False
