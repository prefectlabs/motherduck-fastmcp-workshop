"""Rebuild data/311_cases.csv.gz from DataSF.

The workshop ships a fixed snapshot so every attendee sees the same numbers.
Run this only to refresh the snapshot for a new week:

    uv run python scripts/fetch_snapshot.py 2026-10-12 2026-10-19
"""

import csv
import gzip
import io
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATASET_URL = "https://data.sf.gov/resource/vw6y-z8j6.csv"
COLUMNS = [
    "service_request_id",
    "requested_datetime",
    "closed_date",
    "status_description",
    "agency_responsible",
    "service_name",
    "service_subtype",
    "address",
    "analysis_neighborhood",
    "neighborhoods_sffind_boundaries",
    "source",
]
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "311_cases.csv.gz"


def fetch(start: str, end: str) -> list[dict[str, str]]:
    query = urllib.parse.urlencode(
        {
            "$select": ",".join(COLUMNS),
            "$where": f"requested_datetime >= '{start}T00:00:00' AND requested_datetime < '{end}T00:00:00'",
            "$order": "requested_datetime",
            "$limit": "50000",
        }
    )
    with urllib.request.urlopen(f"{DATASET_URL}?{query}", timeout=120) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main(start: str, end: str) -> None:
    rows = [row for row in fetch(start, end) if row["source"] != "Test"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    OUTPUT.write_bytes(gzip.compress(buffer.getvalue().encode("utf-8"), mtime=0))
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
