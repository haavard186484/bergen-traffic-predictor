"""Local user interface for the frozen Bergen Traffic Predictor model."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from src.config import MODEL_VERSION, TRAFFIC_POINT_ID
from src.data.traffic_history import fetch_required_traffic_history
from src.models.prediction import (
    MODEL_ARTIFACT_PATH,
    forecast_timestamp,
    load_frozen_model,
    predict_one_hour_ahead,
)

st.set_page_config(page_title="Bergen Traffic Predictor", page_icon="🚗")
st.title("Bergen Traffic Predictor")
st.write("Predikerer trafikkvolum én time frem i tid ved Danmarks plass.")
st.caption(f"Modellversjon: `{MODEL_VERSION}`")

st.info(
    "Tidspunktet tolkes i Europe/Oslo. Appen henter nødvendig trafikkhistorikk "
    "fra Statens vegvesens Traffic Data API. Ferdig aggregerte timer publiseres "
    "med forsinkelse, så standardtidspunktet er tre timer tilbake i tid."
)

with st.form("prediction-input"):
    default_timestamp = (
        datetime.now(ZoneInfo("Europe/Oslo")) - timedelta(hours=3)
    ).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    timestamp = st.datetime_input("Forecast-tidspunkt (t)", value=default_timestamp, step=timedelta(hours=1))
    st.caption("Prediksjonen gjelder trafikkvolumet ved t + 1 time.")
    submitted = st.form_submit_button("Prediker")

if submitted:
    try:
        local_timestamp = forecast_timestamp(timestamp)
        frozen_model = load_frozen_model(MODEL_ARTIFACT_PATH)
        history = fetch_required_traffic_history(local_timestamp)
        prediction = predict_one_hour_ahead(frozen_model, local_timestamp, history)
    except ValueError as error:
        st.error(str(error))
    except RuntimeError as error:
        st.error(f"Kunne ikke hente trafikkhistorikk: {error}")
    except FileNotFoundError as error:
        st.error(str(error))
    else:
        st.caption(f"Hentet fra trafikkpunkt `{TRAFFIC_POINT_ID}`.")
        st.dataframe(
            {"tidspunkt": [f"t − {lag}" for lag in history], "kjøretøy/time": list(history.values())},
            hide_index=True,
            use_container_width=True,
        )
        st.metric("Predikert trafikkvolum ved t + 1", f"{prediction:.0f} kjøretøy/time")

st.subheader("Begrensninger")
st.markdown(
    "- Modellen gjelder ett registreringspunkt: Danmarks plass (`14630V805616`).\n"
    "- Den henter observerte trafikkverdier ved t−1, t−2, t−24 og t−168 fra "
    "Traffic Data API. Ved API-feil, målegap eller ukjent historikk gis ingen prediksjon.\n"
    "- Modellen bruker deterministiske norske kalenderfeatures og ingen værdata, "
    "værvarsel eller Frost-konfigurasjon.\n"
    "- Resultatene er et estimat. Frosset sluttevaluering på 2025 ga MAE 102,35 "
    "og RMSE 149,62 på 8 760 forecast-rader."
)
