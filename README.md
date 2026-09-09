# dca-scheduler

I got tired of paying exchange recurring buy fees (Coinbase charges way too much for automated buys), so I wrote this daemon. It places spot market buys on a schedule using exchange API keys and records fills into a local SQLite database.

It adds random jitter to the execution window so you aren't hitting the exchange at the exact second every week.

## Install

```bash
pip install -e .
```

Needs Python 3.11+.

## Config

Put a `config.toml` in your working directory or pass `--config /path/to/config.toml`:

```toml
[exchange]
name = "kraken" # kraken, binance, coinbase
api_key = "YOUR_KEY"
api_secret = "YOUR_SECRET"
passphrase = "" # only needed for coinbase legacy

[schedule]
pair = "BTC/USD"
amount_usd = 50.0
cron = "0 9 * * 1" # cron format
jitter_minutes = 30 # random offset up to +/- 30 mins
max_slippage_pct = 1.5 # abort if current price deviates too much

[storage]
db_path = "~/.dca/history.db"

[notifications]
# optional webhook (discord/slack format or raw telegram bot url)
webhook_url = "https://discord.com/api/webhooks/..."
enable_on_success = true
enable_on_failure = true
```

## Usage

Run the daemon:

```bash
dca run --config config.toml
```

Validate credentials, check balances, and preview the next trigger time:

```bash
dca check --config config.toml
```

Show fill history and totals:

```bash
dca history --limit 20
```

Export history to CSV:

```bash
dca export --output fills.csv
```

## Running with systemd

Put something like this in `~/.config/systemd/user/dca.service`:

```ini
[Unit]
Description=DCA Buy Daemon
After=network.target

[Service]
ExecStart=/home/user/.local/bin/dca run --config /home/user/.config/dca/config.toml
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
```

Then:
```bash
systemctl --user daemon-reload
systemctl --user enable --now dca.service
```

<!-- checked: 2026-09-09 -->
