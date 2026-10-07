"""Minimal user interface for the Bergen Traffic Predictor."""

import streamlit as st


st.set_page_config(page_title="Bergen Traffic Predictor", page_icon="🚗")
st.title("Bergen Traffic Predictor")
st.write("Predikerer trafikkvolum én time frem i tid.")

st.info(
    "Modell og datakilde er ikke koblet til ennå. "
    "Bruk appen som startpunkt når første modellartefakt er klar."
)

with st.form("prediction-input"):
    timestamp = st.datetime_input("Tidspunkt")
    temperature = st.number_input("Temperatur (°C)", value=7.0)
    precipitation = st.number_input("Nedbør (mm)", min_value=0.0, value=0.0)
    submitted = st.form_submit_button("Prediker")

if submitted:
    st.warning("Prediksjon er ikke implementert ennå.")
    st.caption(f"Mottok tidspunkt {timestamp}, temperatur {temperature} °C og {precipitation} mm nedbør.")
