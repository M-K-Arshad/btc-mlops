import json
import os
import pickle
import time
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, request
from statsmodels.tsa.arima.model import ARIMA

app = Flask(__name__)
START = time.time()
MODEL_DIRS = [
    os.getenv("MODEL_DIR", "/app/models"),
    "/app/bundled_models",
    "models",
]
STATE = {"model": None, "meta": {}}


def load_model():
    """Load the first valid model. Only swap it in if loading fully succeeds."""
    errors = []
    for d in MODEL_DIRS:
        path = os.path.join(d, "model.pkl")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                model = pickle.load(f)
            with open(os.path.join(d, "metrics.json")) as f:
                meta = json.load(f)
            STATE["model"], STATE["meta"] = model, meta
            return True
        except Exception as e:
            errors.append(f"{d}: {e}")
            app.logger.exception("Failed to load model from %s", d)
    if errors:
        raise RuntimeError("; ".join(errors))
    return False


try:
    load_model()
except Exception:
    app.logger.exception("Startup model load failed")


load_model()


@app.get("/health")
def health():
    return jsonify(
        status="ok",
        uptime_seconds=round(time.time() - START, 1),
        model_loaded=STATE["model"] is not None,
        model_version=STATE["meta"].get("version", "none"),
    )


@app.get("/metrics")
def metrics():
    if not STATE["meta"]:
        return jsonify(error="No metrics available"), 503
    return jsonify(STATE["meta"]["metrics"])


@app.post("/predict")
def predict():
    try:
        body = request.get_json(silent=True)
        if request.data and body is None:
            return jsonify(error="Invalid JSON body"), 400
        body = body or {}

        days = body.get("forecast_days", 7)
        if type(days) is not int or not 1 <= days <= 30:
            return jsonify(error="forecast_days must be an integer 1-30"), 400

        history = body.get("history")
        if history is not None:
            if (
                not isinstance(history, list)
                or len(history) < 30
                or not all(isinstance(x, (int, float)) for x in history)
            ):
                return (
                    jsonify(error="history must be a list of >= 30 numbers"),
                    400,
                )
            model = ARIMA(history, order=(5, 1, 0)).fit()
            start = date.today()
        else:
            if STATE["model"] is None:
                return jsonify(error="Model not loaded"), 503
            model = STATE["model"]
            start = datetime.strptime(STATE["meta"]["last_date"], "%Y-%m-%d").date()

        preds = model.forecast(steps=days)
        forecast = [
            {
                "date": str(start + timedelta(days=i + 1)),
                "predicted_close": round(float(p), 2),
            }
            for i, p in enumerate(preds)
        ]
        return jsonify(forecast_days=days, forecast=forecast)
    except Exception as e:
        app.logger.exception("Prediction failed")
        return jsonify(error=str(e)), 500


@app.post("/reload")
def reload_model():
    if load_model():
        return jsonify(status="reloaded", model_version=STATE["meta"]["version"])
    return jsonify(error="No model found"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
