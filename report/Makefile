PYTHON ?= python3
LATEXMK ?= latexmk
TEXCOUNT ?= texcount

PDF := bergen-traffic-predictor-report.pdf
BUILD_DIR := build
SOURCES := main.tex references.bib $(wildcard sections/*.tex) figures/pipeline.tex
ERROR_DATA := figures/error_by_hour.csv

.PHONY: all clean count

all: $(PDF)

$(ERROR_DATA): scripts/generate_report_assets.py ../docs/latency-robust-model-evaluation.md
	$(PYTHON) scripts/generate_report_assets.py

$(PDF): $(SOURCES) $(ERROR_DATA)
	mkdir -p $(BUILD_DIR)
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
		-outdir=$(BUILD_DIR) main.tex
	cp $(BUILD_DIR)/main.pdf $(PDF)

count:
	$(TEXCOUNT) -inc -sum main.tex

clean:
	$(LATEXMK) -C -outdir=$(BUILD_DIR) main.tex
	rm -rf $(BUILD_DIR)
