"""Dashboard regression tests with deterministic traffic, without network calls."""

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import streamlit_app as ui


@pytest.fixture
def history():
    hours = pd.date_range("2026-06-01", periods=170, freq="h", tz="UTC")
    return pd.DataFrame({"timestamp": hours, "traffic_volume": range(170)})


def test_comparison_uses_target_not_model_anchor(history):
    target = history.timestamp.iloc[-1]
    assert ui.previous_week(history, target) == 1
    assert ui.percentage_difference(2, 1) == 100
    assert ui.percentage_difference(2, 0) is None
    assert ui.percentage_difference(2, None) is None
    assert ui.previous_week(history.drop(index=1), target) is None


@pytest.mark.parametrize("day,count", [("2026-03-29", 23), ("2026-10-25", 25)])
def test_dst_hours_are_unique_and_exact(day, count):
    hours = ui.target_hours(pd.Timestamp(day).date())
    assert len(hours) == count
    assert hours.is_unique
    for target in hours:
        assert (
            ui.previous_week(
                pd.DataFrame(
                    {"timestamp": [target - pd.Timedelta(hours=168)], "traffic_volume": [42]}
                ),
                target,
            )
            == 42
        )
    if count == 25:
        repeated = [h for h in hours if h.hour == 2]
        assert repeated[0].utcoffset() != repeated[1].utcoffset()
        assert "+0200" in ui.interval_label(repeated[0])
        assert "+0100" in ui.interval_label(repeated[0])


def test_chart_splits_missing_rows_and_nulls(history):
    history = history.drop(index=140)
    history.loc[145, "traffic_volume"] = float("nan")
    chart = ui.chart_history(history, history.timestamp.iloc[-1] + pd.Timedelta(hours=1))
    assert len(chart) == 73
    assert chart.traffic_volume.isna().sum() == 3
    valid = chart.dropna(subset=["traffic_volume"])
    for _, group in valid.groupby("segment"):
        assert (group.timestamp.diff().dropna() == pd.Timedelta(hours=1)).all()


class DummyModel:
    def predict(self, inputs):
        assert inputs.iloc[0].tolist() == [144, 120, 0]
        return [150.0]


@pytest.fixture
def bundle():
    return {
        "metadata": {"traffic_lags": [24, 48, 168]},
        "feature_columns": ["traffic_24h_ago", "traffic_48h_ago", "traffic_168h_ago"],
        "model": DummyModel(),
    }


def test_missing_comparison_does_not_block_model(history, bundle):
    target = history.timestamp.iloc[-1]
    history = history.drop(index=1)
    prediction, _ = ui.predict_forecast(target, bundle, history)
    assert prediction == 150
    assert ui.previous_week(history, target) is None
    with pytest.raises(ValueError, match="Mangler nødvendige"):
        ui.predict_forecast(target, bundle, history.drop(index=0))


def app():
    # Import the same patched module inside the Streamlit runner.
    return AppTest.from_string("from app.streamlit_app import main\nmain()").run()


def test_app_default_and_missing_model(monkeypatch):
    def missing():
        raise FileNotFoundError

    monkeypatch.setattr(ui, "load_model", missing)
    at = app()
    assert not at.exception
    assert at.radio[0].value == "Neste time"
    assert at.button[0].label == "Vis prognose"
    at.button[0].click().run()
    assert "Modellen er ikke klargjort" in at.error[0].value
    assert not at.exception


@pytest.mark.parametrize(
    "error,message",
    [
        (RuntimeError("network"), "Trafikkdata kunne ikke hentes"),
        (ValueError("missing"), "Det mangler gyldige trafikkdata"),
    ],
)
def test_app_data_failures(monkeypatch, bundle, error, message):
    monkeypatch.setattr(ui, "load_model", lambda: bundle)

    def fail(*args):
        raise error

    monkeypatch.setattr(ui, "_traffic_history", fail)
    at = app().button[0].click().run()
    assert not at.exception
    assert message in (at.error or at.warning)[0].value


def test_app_success_with_missing_comparison(monkeypatch, bundle):
    monkeypatch.setattr(ui, "load_model", lambda: bundle)

    def fetch(anchor, lag):
        hours = pd.date_range(anchor - pd.Timedelta(hours=lag), anchor, freq="h")
        return pd.DataFrame({"timestamp": hours, "traffic_volume": range(len(hours))}).drop(1)

    monkeypatch.setattr(ui, "_traffic_history", fetch)
    at = app().button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "150"
    assert at.metric[1].value == "Ikke tilgjengelig"
    assert any("Hentet" in c.value for c in at.caption)
    at.radio[0].set_value("Historisk tidspunkt").run()
    assert not at.exception
    assert len(at.metric) == 0  # Never leave a stale forecast under a different selection.


def test_chart_passes_tabular_data_and_segment_encoding(monkeypatch, history):
    captured = {}

    def capture(data, spec, **kwargs):
        captured.update(data=data, spec=spec)

    monkeypatch.setattr(ui.st, "vega_lite_chart", capture)
    target = history.timestamp.iloc[-1] + pd.Timedelta(hours=1)
    ui.show_chart(history.drop(index=140), target, 150)
    data = captured["data"]
    assert isinstance(data, pd.DataFrame)
    assert {"local_time", "traffic_volume", "segment", "kind"} <= set(data.columns)
    assert data.iloc[-1]["kind"] == "Prognose"
    assert data.iloc[-1]["traffic_volume"] == 150
    assert captured["spec"]["layer"][0]["encoding"]["detail"]["field"] == "segment"
    assert len(captured["spec"]["encoding"]["x"]["scale"]["domain"]) == 73
