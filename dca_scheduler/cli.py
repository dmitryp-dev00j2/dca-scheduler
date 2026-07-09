import argparse
import logging
import sys
from dca_scheduler.scheduler import Scheduler
from dca_scheduler.store import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dca-scheduler", description="DCA order automation daemon")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="start dca daemon loop")
    run_p.add_argument("--pair", default="BTC/USDT", help="market symbol (default BTC/USDT)")
    run_p.add_argument("--amount", type=float, required=True, help="quote amount to spend per order")
    run_p.add_argument("--interval", type=int, default=86400, help="interval between orders in seconds")
    run_p.add_argument("--jitter", type=int, default=300, help="max random seconds added to sleep")
    run_p.add_argument("--db", default="dca.db", help="sqlite db path")

    hist_p = sub.add_parser("history", help="show executed order logs")
    hist_p.add_argument("--db", default="dca.db", help="sqlite db path")
    hist_p.add_argument("--limit", type=int, default=20, help="max records to display")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        store = Store(args.db)
        sched = Scheduler(
            pair=args.pair,
            amount=args.amount,
            interval_seconds=args.interval,
            jitter_seconds=args.jitter,
            store=store,
        )
        try:
            sched.run()
        except KeyboardInterrupt:
            sched.stop()
            sys.exit(0)

    elif args.command == "history":
        store = Store(args.db)
        records = store.get_orders(limit=args.limit)
        if not records:
            print("No executed orders found.")
            return
        for r in records:
            print(f"{r['timestamp']} | {r['pair']} | {r['amount']} USDT | fill: {r['filled_price']} | id: {r['order_id']}")


if __name__ == "__main__":
    main()
