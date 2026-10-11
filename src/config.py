"""Shared paths and project-wide constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
TIMEZONE = "Europe/Oslo"
TARGET_COLUMN = "target_traffic"
MODEL_VERSION = "traffic-hgb-calendar-v1"
TRAFFIC_POINT_ID = "14630V805616"
