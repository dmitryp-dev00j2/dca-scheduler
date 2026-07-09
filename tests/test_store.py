import tempfile
from pathlib import Path
import pytest

from dca_scheduler.store import DBStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_dca.db"
        s = DBStore(str(db_path))
        s.init_db()
        yield s
        s.close()


def test_save_and_retrieve_order(store):
    order_id = store.record_order(
        exchange="kraken",
        pair="BTC/USD",
        side="buy",
        fiat_amount=50.0,
        crypto_amount=0.00055,
        price=90909.09,
        fee=0.20,
        tx_id="TX-12345",
        status="filled",
    )
    assert order_id > 0

    orders = store.list_orders(limit=10)
    assert len(orders) == 1
    row = orders[0]
    assert row["pair"] == "BTC/USD"
    assert row["fiat_amount"] == 50.0
    assert row["crypto_amount"] == 0.00055
    assert row["status"] == "filled"


def test_total_spent_by_pair(store):
    store.record_order("kraken", "BTC/USD", "buy", 50.0, 0.0005, 100000.0, 0.2, "tx1", "filled")
    store.record_order("kraken", "BTC/USD", "buy", 50.0, 0.0005, 100000.0, 0.2, "tx2", "filled")
    store.record_order("kraken", "ETH/USD", "buy", 25.0, 0.01, 2500.0, 0.1, "tx3", "filled")
    # failed orders shouldn't count towards totals
    store.record_order("kraken", "BTC/USD", "buy", 50.0, 0.0, 0.0, 0.0, "tx4", "failed")

    stats = store.get_summary()
    assert stats["BTC/USD"]["total_spent"] == 100.0
    assert stats["BTC/USD"]["total_bought"] == 0.0010
    assert stats["ETH/USD"]["total_spent"] == 25.0


