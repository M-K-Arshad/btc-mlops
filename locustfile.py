"""
Locust load test for the BTC Forecast API.
Run: locust -f locustfile.py --host http://btc-forecast.local
"""

import random

from locust import HttpUser, between, task


class ForecastUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def predict_default(self):
        self.client.post(
            "/predict",
            json={"forecast_days": random.choice([7, 14])},
            name="/predict (model)",
        )

    @task(2)
    def predict_custom_history(self):
        # Heavier request: fits a new ARIMA model on the given history (CPU-heavy)
        base = random.uniform(60000, 100000)
        history = [base + random.uniform(-2000, 2000) for _ in range(60)]
        self.client.post(
            "/predict",
            json={"forecast_days": 7, "history": history},
            name="/predict (custom history)",
        )

    @task(1)
    def health(self):
        self.client.get("/health")

    @task(1)
    def metrics(self):
        self.client.get("/metrics")