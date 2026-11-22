import os

import pandas as pd
import requests

COLS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def _from_yahoo(period):
    import yfinance as yf

    df = yf.download(
        "BTC-USD", period=period, interval="1d", auto_adjust=False, timeout=20
    )
    if df.empty:
        raise ValueError("Yahoo returned no data")
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.reset_index()[COLS]


def _from_binance(days):
    for host in ["https://data-api.binance.vision", "https://api.binance.com"]:
        try:
            r = requests.get(
                f"{host}/api/v3/klines",
                params={"symbol": "BTCUSDT", "interval": "1d", "limit": days},
                timeout=20,
            )
            r.raise_for_status()
            df = pd.DataFrame(r.json()).iloc[:, :6]
            df.columns = COLS
            df["Date"] = pd.to_datetime(df["Date"], unit="ms").dt.date
            return df.astype({c: float for c in COLS[1:]})
        except Exception as e:
            print(f"Binance {host} failed: {e}")
    raise ValueError("Binance failed")


def _from_coingecko(days):
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
        params={"vs_currency": "usd", "days": min(days, 365), "interval": "daily"},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    df = pd.DataFrame(j["prices"], columns=["ts", "Close"])
    df["Volume"] = [v[1] for v in j["total_volumes"]]
    df["Date"] = pd.to_datetime(df["ts"], unit="ms").dt.date
    df["Open"] = df["High"] = df["Low"] = df[
        "Close"
    ]  # CoinGecko free API gives close only
    return df.drop_duplicates("Date", keep="last")[COLS]


def fetch_btc(out="data/raw/btc.csv", period="2y", days=730):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for name, fn in [
        ("Yahoo", lambda: _from_yahoo(period)),
        ("Binance", lambda: _from_binance(days)),
        ("CoinGecko", lambda: _from_coingecko(days)),
    ]:
        try:
            df = fn()
            print(f"Fetched {len(df)} rows from {name}")
            df.to_csv(out, index=False)
            return out
        except Exception as e:
            print(f"{name} failed: {e}")
    raise RuntimeError("All data sources failed - check your internet connection")
