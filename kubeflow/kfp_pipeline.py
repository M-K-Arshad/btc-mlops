"""
Kubeflow Pipeline: BTC 7-day closing price forecast.

ingest_data -> build_features -> train_model
Each step is a separate component that runs in its own container.

Compile:      python kubeflow/btc_kfp_pipeline.py
Local test:   python kubeflow/btc_kfp_pipeline.py --run-local
"""

import sys

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

BASE_IMAGE = "python:3.10-slim"
PKGS = [
    "pandas==2.2.2",
    "numpy==1.26.4",
    "scipy==1.13.1",
    "statsmodels==0.14.2",
    "requests",
]


# ---------------------------------------------------------------- 1. Ingest
@dsl.component(base_image=BASE_IMAGE, packages_to_install=PKGS)
def ingest_data(raw_data: Output[Dataset], days: int = 730):
    """Download daily BTC OHLCV data (Binance, fallback CoinGecko)."""
    import pandas as pd
    import requests

    cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    df = None
    for host in ["https://data-api.binance.vision", "https://api.binance.com"]:
        try:
            r = requests.get(
                f"{host}/api/v3/klines",
                params={"symbol": "BTCUSDT", "interval": "1d", "limit": days},
                timeout=20,
            )
            r.raise_for_status()
            df = pd.DataFrame(r.json()).iloc[:, :6]
            df.columns = cols
            df["Date"] = pd.to_datetime(df["Date"], unit="ms").dt.date
            print(f"Fetched {len(df)} rows from {host}")
            break
        except Exception as e:
            print(f"{host} failed: {e}")

    if df is None:
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
        df["Open"] = df["High"] = df["Low"] = df["Close"]
        df = df.drop_duplicates("Date", keep="last")[cols]
        print(f"Fetched {len(df)} rows from CoinGecko")

    df.to_csv(raw_data.path, index=False)


# ---------------------------------------------------------------- 2. Features
@dsl.component(base_image=BASE_IMAGE, packages_to_install=PKGS)
def build_features(raw_data: Input[Dataset], processed_data: Output[Dataset]):
    """Clean data and add MA7, MA30 and 7-day volatility."""
    import pandas as pd

    df = pd.read_csv(raw_data.path, parse_dates=["Date"]).dropna()
    df = df.sort_values("Date")
    df["MA7"] = df["Close"].rolling(7).mean()
    df["MA30"] = df["Close"].rolling(30).mean()
    df["Volatility7"] = df["Close"].pct_change().rolling(7).std()
    df = df.dropna()
    df.to_csv(processed_data.path, index=False)
    print(f"Features built: {len(df)} rows, columns={list(df.columns)}")


# ---------------------------------------------------------------- 3. Train
@dsl.component(base_image=BASE_IMAGE, packages_to_install=PKGS)
def train_model(
    processed_data: Input[Dataset],
    model: Output[Model],
    metrics: Output[Metrics],
    max_mape: float = 15.0,
):
    """Evaluate ARIMA on the last 7 days, then train on all data and save."""
    import pickle

    import numpy as np
    import pandas as pd
    from statsmodels.tsa.arima.model import ARIMA

    df = pd.read_csv(processed_data.path, parse_dates=["Date"])
    y = df["Close"].values

    pred = ARIMA(y[:-7], order=(5, 1, 0)).fit().forecast(steps=7)
    err = y[-7:] - pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(err / y[-7:])) * 100)

    metrics.log_metric("MAE", mae)
    metrics.log_metric("RMSE", rmse)
    metrics.log_metric("MAPE", mape)
    print(f"MAE={mae:.2f} RMSE={rmse:.2f} MAPE={mape:.2f}%")

    if mape > max_mape:
        raise ValueError(f"Model rejected: MAPE {mape:.2f}% > {max_mape}%")

    final = ARIMA(y, order=(5, 1, 0)).fit()
    with open(model.path, "wb") as f:
        pickle.dump(final, f)
    model.metadata["framework"] = "statsmodels-ARIMA(5,1,0)"
    model.metadata["last_date"] = str(df["Date"].iloc[-1].date())
    model.metadata["MAPE"] = mape


# ---------------------------------------------------------------- Pipeline
@dsl.pipeline(
    name="btc-forecast-pipeline",
    description="Ingest BTC data, build features, train 7-day ARIMA forecaster",
)
def btc_pipeline(days: int = 730, max_mape: float = 15.0):
    ingest = ingest_data(days=days)
    ingest.set_display_name("Ingest BTC data")

    feats = build_features(raw_data=ingest.outputs["raw_data"])
    feats.set_display_name("Build features")

    train = train_model(
        processed_data=feats.outputs["processed_data"], max_mape=max_mape
    )
    train.set_display_name("Train & evaluate model")

    for task in (ingest, feats, train):
        task.set_cpu_limit("1").set_memory_limit("1G")


if __name__ == "__main__":
    out = "kubeflow/btc_kfp_pipeline.yaml"
    compiler.Compiler().compile(pipeline_func=btc_pipeline, package_path=out)
    print(f"Compiled pipeline -> {out}")

    if "--run-local" in sys.argv:
        from kfp import local

        local.init(runner=local.SubprocessRunner(use_venv=False))
        btc_pipeline()
