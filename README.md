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
name = "kraken" # or "coinbase"
api_key = "YOUR_KEY"
api_secret = "YOUR_SECRET"

[schedule]
pair = "BTC/USD"
amount_usd = 50.0
cron = "0 9 * * 1" # every monday at 9am
jitter_minutes = 45 # random offset up to +/- 45 mins

[storage]
db_path = "~/.dca/history.db"
```

## Usage

Run the daemon in foreground:

```bash
dca run --config config.toml
```

Check credentials and print the next scheduled run:

```bash
dca check --config config.toml
```

Show fill history:

```bash
dca history
```
