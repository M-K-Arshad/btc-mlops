import os
import pandas as pd


def preprocess(raw="data/raw/btc.csv", out="data/processed/btc_features.csv"):
    df = pd.read_csv(raw, parse_dates=["Date"]).dropna().sort_values("Date")
    df["MA7"] = df["Close"].rolling(7).mean()
    df["MA30"] = df["Close"].rolling(30).mean()
    df["Volatility7"] = df["Close"].pct_change().rolling(7).std()
    df = df.dropna()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False)
    return out