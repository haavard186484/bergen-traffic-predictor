"""Interactive forecast UI for the frozen latency-robust traffic model."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
import streamlit as st

from src.data.traffic_api import download_hourly_traffic
from src.features.build_features import create_features

POINT_ID = "14630V805616"
MODEL_PATH = Path("models/traffic_hgb_latency_robust_v1.joblib")
OSLO = ZoneInfo("Europe/Oslo")


def load_model(path: Path = MODEL_PATH) -> dict[str, object]:
    """Load the local frozen model bundle with its feature metadata."""
    if not path.exists():
        raise FileNotFoundError(
            f"Modellartefakten mangler: {path}. Kjør python -m scripts.run_latency_robust_model først."
        )
    return joblib.load(path)


def _traffic_history(anchor: pd.Timestamp, max_lag: int) -> pd.DataFrame:
    """Fetch only the traffic observations needed for the forecast's lagged inputs."""
    start = anchor - pd.Timedelta(hours=max_lag)
    raw = download_hourly_traffic(POINT_ID, start.isoformat(), anchor.isoformat())
    if raw.empty:
        raise ValueError("Traffic Data API returnerte ingen trafikkhistorikk")
    history = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(raw["Fra"], utc=True),
            "traffic_volume": pd.to_numeric(raw["Trafikkmengde"], errors="coerce"),
        }
    )
    # The anchor itself is only a feature timestamp; its observed traffic is
    # intentionally not used. Add it when the API's end boundary excludes it.
    if not (history["timestamp"] == anchor).any():
        history = pd.concat(
            [history, pd.DataFrame({"timestamp": [anchor], "traffic_volume": [float("nan")]})],
            ignore_index=True,
        )
    if history["timestamp"].duplicated().any():
        raise ValueError("Traffic Data API returnerte dupliserte tidspunkter")
    return history.sort_values("timestamp").reset_index(drop=True)


def predict_forecast(
    forecast_timestamp: datetime, bundle: dict[str, object]
) -> tuple[float, pd.Series]:
    """Predict traffic at ``forecast_timestamp`` from latency-safe history only."""
    if forecast_timestamp.tzinfo is None:
        forecast_timestamp = forecast_timestamp.replace(tzinfo=OSLO)
    target = pd.Timestamp(forecast_timestamp).tz_convert("UTC").floor("h")
    anchor = target - pd.Timedelta(hours=1)
    metadata = bundle["metadata"]
    traffic_lags = tuple(int(hours) for hours in metadata["traffic_lags"])
    history = _traffic_history(anchor, max(traffic_lags))
    features = create_features(history, calendar_event_features=True, traffic_lags=traffic_lags)
    row = features.loc[features["timestamp"] == anchor]
    if len(row) != 1:
        raise ValueError("Kunne ikke bygge feature-raden for forecast-tidspunktet")
    feature_columns = list(bundle["feature_columns"])
    inputs = row.iloc[0][feature_columns]
    missing = inputs[inputs.isna()].index.tolist()
    if missing:
        raise ValueError(f"Mangler nødvendige trafikkinput: {', '.join(missing)}")
    prediction = float(bundle["model"].predict(pd.DataFrame([inputs], columns=feature_columns))[0])
    return prediction, inputs


st.set_page_config(page_title="Bergen Traffic Predictor", page_icon="🚗")
st.title("Bergen Traffic Predictor")
st.write("Predikerer trafikkvolum én time frem i tid ved Danmarks plass.")
st.caption(
    "Latensrobust modell: kalender samt trafikk ved t−24, t−48 og t−168. "
    "Den bruker ikke t−1, t−2 eller værdata."
)

try:
    model_bundle = load_model()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

default_target = (datetime.now(OSLO) + timedelta(hours=1)).replace(
    minute=0, second=0, microsecond=0
)
with st.form("prediction-input"):
    forecast_time = st.datetime_input("Forecast-tidspunkt (Europe/Oslo)", value=default_target)
    submitted = st.form_submit_button("Prediker")

if submitted:
    try:
        prediction, inputs = predict_forecast(forecast_time, model_bundle)
    except (RuntimeError, ValueError) as error:
        st.error(f"Kunne ikke lage prediksjon: {error}")
    else:
        st.metric("Predikert trafikkvolum", f"{prediction:.0f} kjøretøy/time")
        st.caption("Mottatte trafikkinput fra Statens vegvesen")
        st.dataframe(inputs.rename("verdi"), use_container_width=True)
