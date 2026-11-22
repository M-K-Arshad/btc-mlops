import numpy as np

from app import app

client = app.test_client()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["status"] == "ok"


def test_metrics():
    r = client.get("/metrics")
    assert r.status_code in (200, 503)


def test_predict_default():
    r = client.post("/predict", json={})
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert len(r.json["forecast"]) == 7


def test_bad_days():
    r = client.post("/predict", json={"forecast_days": "x"})
    assert r.status_code == 400


def test_bad_json():
    r = client.post("/predict", data="{bad", content_type="application/json")
    assert r.status_code == 400


def test_predict_with_history():
    hist = list(np.linspace(60000, 65000, 60) + np.random.randn(60) * 100)
    r = client.post("/predict", json={"forecast_days": 7, "history": hist})
    assert r.status_code == 200
    assert len(r.json["forecast"]) == 7
