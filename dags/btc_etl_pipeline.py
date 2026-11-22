"""
BTC ETL Pipeline
Daily: fetch BTC data -> feature engineering -> retrain + evaluate -> reload API.
"""

import sys
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow/src")
from etl_fetch import fetch_btc  # noqa: E402
from preprocess import preprocess  # noqa: E402
from train_forecast import train  # noqa: E402

BASE = "/opt/airflow"
RAW = f"{BASE}/data/raw/btc.csv"
PROCESSED = f"{BASE}/data/processed/btc_features.csv"
MODEL_DIR = f"{BASE}/models"
API_RELOAD_URL = "http://api:5000/reload"


def reload_api():
    """Tell the Flask service to re-read the updated model files."""
    r = requests.post(API_RELOAD_URL, timeout=30)
    print(f"API responded {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


default_args = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="btc_etl_pipeline",
    description="Daily BTC fetch, feature engineering, retraining and API reload",
    start_date=datetime(2026, 11, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["btc", "mlops"],
    doc_md=__doc__,
) as dag:

    fetch_data = PythonOperator(
        task_id="fetch_data",
        python_callable=fetch_btc,
        op_kwargs={"out": RAW},
    )

    preprocess_features = PythonOperator(
        task_id="preprocess_features",
        python_callable=preprocess,
        op_kwargs={"raw": RAW, "out": PROCESSED},
    )

    train_evaluate_register = PythonOperator(
        task_id="train_evaluate_register",
        python_callable=train,
        op_kwargs={"data": PROCESSED, "model_dir": MODEL_DIR, "max_mape": 15.0},
    )

    reload_api_model = PythonOperator(
        task_id="reload_api_model",
        python_callable=reload_api,
    )

    fetch_data >> preprocess_features >> train_evaluate_register >> reload_api_model
