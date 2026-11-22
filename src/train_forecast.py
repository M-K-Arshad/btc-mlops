import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA


def evaluate(y, p):
    e = y - p
    return {
        "MAE": float(np.mean(np.abs(e))),
        "RMSE": float(np.sqrt(np.mean(e**2))),
        "MAPE": float(np.mean(np.abs(e / y)) * 100),
    }


def train(
    data="data/processed/btc_features.csv", model_dir="models", max_mape=10.0
):
    df = pd.read_csv(data, parse_dates=["Date"])
    close = df["Close"].values
    test_pred = ARIMA(close[:-7], order=(5, 1, 0)).fit().forecast(steps=7)
    metrics = evaluate(close[-7:], test_pred)
    if metrics["MAPE"] > max_mape:
        raise ValueError(
            f"Rejected: MAPE {metrics['MAPE']:.2f}% > {max_mape}%"
        )
    final = ARIMA(close, order=(5, 1, 0)).fit()
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(final, f"{model_dir}/model.pkl")
    meta = {
        "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "last_date": df["Date"].iloc[-1].strftime("%Y-%m-%d"),
        "metrics": metrics,
    }
    with open(f"{model_dir}/metrics.json", "w") as f:
        json.dump(meta, f, indent=2)
    return meta


if __name__ == "__main__":
    import sys

    sys.path.insert(0, "src")
    from etl_fetch import fetch_btc
    from preprocess import preprocess

    fetch_btc()
    preprocess()
    print(train())
