PYTHON ?= python3
TRAFFIC_POINT_ID ?= 14630V805616
TRAFFIC_FROM ?= 2022-01-01T00:00:00+01:00
TRAFFIC_TO ?= 2026-07-01T00:00:00+02:00
RAW_TRAFFIC ?= data/raw/traffic_2022_2026_h1.csv

.PHONY: download-traffic prepare-traffic refresh-traffic train-latency-robust-model build-app-model download-weather test

download-traffic:
	$(PYTHON) -m scripts.download_traffic_data \
		--point-id $(TRAFFIC_POINT_ID) \
		--from $(TRAFFIC_FROM) \
		--to $(TRAFFIC_TO) \
		--output $(RAW_TRAFFIC)

prepare-traffic:
	$(PYTHON) -m scripts.prepare_traffic_dataset $(RAW_TRAFFIC) --allow-gaps

refresh-traffic: download-traffic prepare-traffic

train-latency-robust-model:
	$(PYTHON) -m scripts.run_latency_robust_model

build-app-model: refresh-traffic train-latency-robust-model

download-weather:
	$(PYTHON) -m scripts.download_weather_data

test:
	$(PYTHON) -m pytest
