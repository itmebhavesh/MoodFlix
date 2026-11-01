import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "instance" / "movies_omdb_10000.csv"


def get_all_movies():
    if not CSV_PATH.exists():
        print(f"Movie CSV not found: {CSV_PATH}")
        return []

    with open(CSV_PATH, "r", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))