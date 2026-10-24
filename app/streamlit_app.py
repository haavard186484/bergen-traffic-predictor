"""Interactive forecast UI for the frozen latency-robust traffic model."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from pickle import UnpicklingError
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
    history = history.loc[(history["timestamp"] >= start) & (history["timestamp"] < anchor)]
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
    forecast_timestamp: datetime, bundle: dict[str, object], history: pd.DataFrame | None = None
) -> tuple[float, pd.Series]:
    """Predict traffic at ``forecast_timestamp`` from latency-safe history only."""
    if forecast_timestamp.tzinfo is None:
        forecast_timestamp = forecast_timestamp.replace(tzinfo=OSLO)
    target = pd.Timestamp(forecast_timestamp).tz_convert("UTC").floor("h")
    anchor = target - pd.Timedelta(hours=1)
    metadata = bundle["metadata"]
    traffic_lags = tuple(int(hours) for hours in metadata["traffic_lags"])
    if history is None:
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


def target_hours(day: date) -> pd.DatetimeIndex:
    """Offer each real Oslo hour, including both occurrences at autumn DST."""
    start = pd.Timestamp(day).tz_localize(OSLO)
    end = pd.Timestamp(day + timedelta(days=1)).tz_localize(OSLO)
    return pd.date_range(start, end, freq="h", inclusive="left")


def interval_label(target: pd.Timestamp) -> str:
    """Show an exact elapsed hour with explicit offsets at DST transitions."""
    start = target.tz_convert(OSLO)
    end = (target + pd.Timedelta(hours=1)).tz_convert(OSLO)
    return f"{start:%d.%m.%Y %H:%M %z} – {end:%d.%m.%Y %H:%M %z} (Europe/Oslo)"


def previous_week(history: pd.DataFrame, target: pd.Timestamp) -> float | None:
    """Look up target−168h, independently of the model's anchor−168h input."""
    values = history.loc[
        history["timestamp"] == target - pd.Timedelta(hours=168), "traffic_volume"
    ].dropna()
    return float(values.iloc[0]) if len(values) == 1 else None


def percentage_difference(prediction: float, comparison: float | None) -> float | None:
    return (
        (prediction / comparison - 1) * 100 if comparison is not None and comparison > 0 else None
    )


def chart_history(history: pd.DataFrame, target: pd.Timestamp) -> pd.DataFrame:
    """Regularize 72 hours without filling gaps; group contiguous observations."""
    hours = pd.date_range(target - pd.Timedelta(hours=72), target, freq="h")
    values = history.set_index("timestamp")["traffic_volume"].reindex(hours)
    frame = values.rename_axis("timestamp").reset_index()
    frame["segment"] = frame["traffic_volume"].isna().cumsum()
    frame["local_time"] = frame["timestamp"].map(
        lambda stamp: stamp.tz_convert(OSLO).strftime("%d.%m. %H:%M %z")
    )
    return frame


def show_chart(history: pd.DataFrame, target: pd.Timestamp, prediction: float) -> None:
    frame = chart_history(history, target)
    # Ordinal local labels preserve repeated DST hours and avoid browser timezone conversion.
    labels = frame["local_time"].tolist()
    observed = frame.dropna(subset=["traffic_volume"])
    records = observed[["local_time", "traffic_volume", "segment"]].to_dict("records")
    records.append({"local_time": labels[-1], "traffic_volume": prediction, "kind": "Prognose"})
    for order, record in enumerate(records[:-1]):
        record["kind"] = "Observert"
        record["order"] = order
    st.vega_lite_chart(
        pd.DataFrame(records),
        {
            "height": 290,
            "encoding": {
                "x": {
                    "field": "local_time",
                    "type": "ordinal",
                    "sort": labels,
                    "scale": {"domain": labels},
                    "axis": {
                        "title": "Tid i Europe/Oslo (UTC-offset vist)",
                        "values": labels[::12] + [labels[-1]],
                        "labelAngle": -25,
                    },
                },
                "y": {
                    "field": "traffic_volume",
                    "type": "quantitative",
                    "axis": {"title": "Kjøretøy/time"},
                    "scale": {"zero": True},
                },
                "color": {
                    "field": "kind",
                    "type": "nominal",
                    "title": None,
                    "scale": {"domain": ["Observert", "Prognose"], "range": ["#17365D", "#007F82"]},
                },
                "tooltip": [
                    {"field": "local_time", "title": "Europe/Oslo"},
                    {"field": "traffic_volume", "title": "Kjøretøy/time", "format": ".0f"},
                    {"field": "kind", "title": "Type"},
                ],
            },
            "layer": [
                {
                    "transform": [{"filter": "datum.kind === 'Observert'"}],
                    "mark": {"type": "line", "point": True, "strokeWidth": 2},
                    "encoding": {
                        "detail": {"field": "segment", "type": "nominal"},
                        "order": {"field": "order", "type": "quantitative"},
                    },
                },
                {
                    "transform": [{"filter": "datum.kind === 'Prognose'"}],
                    "mark": {"type": "point", "shape": "diamond", "filled": True, "size": 180},
                },
            ],
        },
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="Danmarks plass · Trafikkprognose", page_icon="🚗", layout="wide")
    st.markdown(
        """<style>
        .stApp {background: #F5F7FA; color: #17365D;}
        .block-container {max-width: 1120px; padding-top: 3rem; padding-bottom: 3rem;}
        h1, h2, h3 {color: #17365D;}
        div[data-testid="stMetric"] {background: white; border: 1px solid #E0E6EE;
            border-radius: 16px; padding: 1.5rem; min-height: 150px;}
        div[data-testid="stMetricValue"] {color: #17365D;}
        </style>""",
        unsafe_allow_html=True,
    )
    st.caption("BERGEN TRAFFIC PREDICTOR  /  BILTRAFIKK")
    st.title("Danmarks plass")
    st.write("En time frem i tid. En prognose basert på trafikkhistorikk og kalender.")
    st.caption(f"Gjelder ett registreringspunkt ({POINT_ID}), ikke all trafikk på Danmarks plass.")
    mode = st.radio("Velg tidspunkt", ["Neste time", "Historisk tidspunkt"], horizontal=True)
    now = pd.Timestamp.now(tz="UTC")
    target = now.floor("h") + pd.Timedelta(hours=1)
    if mode == "Historisk tidspunkt":
        left, right = st.columns(2)
        day = left.date_input(
            "Dato (Europe/Oslo)",
            value=now.tz_convert(OSLO).date(),
            max_value=now.tz_convert(OSLO).date(),
        )
        hours = target_hours(day)
        hours = hours[hours.tz_convert("UTC") <= now.floor("h")]
        target = right.selectbox(
            "Time (Europe/Oslo)",
            hours.to_list(),
            format_func=lambda stamp: stamp.strftime("%H:%M %z"),
        )
    st.caption(interval_label(target))
    submitted = st.button("Vis prognose", type="primary")
    if submitted:
        st.session_state.pop("forecast_result", None)
        try:
            bundle = load_model()
        except FileNotFoundError:
            st.error("Modellen er ikke klargjort. Kjør `make build-app-model` og prøv igjen.")
            return
        except (OSError, ValueError, EOFError, UnpicklingError, ImportError):
            st.error("Modellfilen kunne ikke leses. Bygg den på nytt med `make build-app-model`.")
            return
        try:
            with st.spinner("Henter trafikkhistorikk fra Statens vegvesen …"):
                anchor = target.tz_convert("UTC") - pd.Timedelta(hours=1)
                history = _traffic_history(anchor, max(bundle["metadata"]["traffic_lags"]))
                fetched_at = pd.Timestamp.now(tz="UTC")
                prediction, inputs = predict_forecast(target, bundle, history)
        except (RuntimeError, OSError, KeyError, TypeError):
            st.error("Trafikkdata kunne ikke hentes fra Statens vegvesen. Prøv igjen om litt.")
            st.caption(
                "Datastatus: ingen ny prognose. Siste forsøk: "
                + datetime.now(OSLO).strftime("%d.%m.%Y %H:%M:%S %z")
            )
            return
        except ValueError as error:
            st.caption(
                "Datastatus: utilstrekkelige data. Siste forsøk: "
                + datetime.now(OSLO).strftime("%d.%m.%Y %H:%M:%S %z")
            )
            st.warning(
                "Det mangler gyldige trafikkdata for dette tidspunktet. "
                "Velg et annet tidspunkt eller prøv igjen senere."
            )
            with st.expander("Tekniske detaljer"):
                st.text(str(error))
            return
        st.session_state["forecast_result"] = (
            target,
            prediction,
            inputs,
            history,
            fetched_at,
            bundle["metadata"],
        )
    result = st.session_state.get("forecast_result")
    if result is None or result[0] != target:
        st.info("Velg tidspunkt og trykk «Vis prognose» for å hente trafikkdata.")
        return
    target, prediction, inputs, history, fetched_at, metadata = result
    st.subheader("Trafikkprognose")
    st.write(interval_label(target))
    comparison = previous_week(history, target)
    change = percentage_difference(prediction, comparison)
    left, right = st.columns([3, 2])
    left.metric("Forventet biltrafikk · kjøretøy/time", f"{prediction:,.0f}".replace(",", " "))
    right.metric(
        "Observert samme target-time forrige uke · kjøretøy/time",
        "Ikke tilgjengelig" if comparison is None else f"{comparison:,.0f}".replace(",", " "),
    )
    if change is not None:
        st.write(
            f"Prognosen er {abs(change):.1f} % {'høyere' if change >= 0 else 'lavere'} "
            "enn observasjonen forrige uke."
        )
    elif comparison is None:
        st.caption("Sammenligningsdata mangler. Modellprognosen kan likevel beregnes.")
    else:
        st.caption("Prosentforskjell vises bare når sammenligningsverdien er positiv.")
    st.caption("Sammenligningsintervall: " + interval_label(target - pd.Timedelta(hours=168)))
    st.subheader("Nylig trafikk og prognose")
    show_chart(history, target, prediction)
    st.caption(
        "Blå linje og punkter: observasjoner. Turkis diamant: prognose. "
        "Målegap og upubliserte timer beholdes åpne. Viser de siste 72 timene før target."
    )
    st.subheader("Datastatus")
    st.caption(
        "Kilde: Statens vegvesen · Hentet "
        + fetched_at.tz_convert(OSLO).strftime("%d.%m.%Y %H:%M:%S %z (Europe/Oslo)")
    )
    available = history.dropna(subset=["traffic_volume"])
    if not available.empty:
        st.write(
            "Siste tilgjengelige observasjon i uttrekket: "
            + interval_label(available["timestamp"].max())
        )
    st.caption(
        "Trafikkdata kan publiseres med forsinkelse. Historiske oppslag bruker data "
        "tilgjengelig nå; tidligere publiseringstidspunkt kan ikke rekonstrueres."
    )
    with st.expander("Tekniske input og modellinformasjon"):
        st.write("Modell: traffic-hgb-latency-robust-v1 · HistGradientBoostingRegressor")
        st.write(
            "Target = t + 1 time. Trafikklag: t−24, t−48 og t−168, samt norske "
            "kalenderfeatures. Ingen værdata. Sammenligningen bruker target−168 timer "
            "(t−167), separat fra modellens t−168-feature."
        )
        st.caption(
            "Trent på 2022–2025. Sluttevaluering 2026 H1: MAE 108,81 kjøretøy/time; "
            "forrige-uke-baseline 211,79 på samme 4 343 rader."
        )
        st.dataframe(inputs.rename("Verdi"), use_container_width=True)
        st.json(metadata)


if __name__ == "__main__":
    main()
