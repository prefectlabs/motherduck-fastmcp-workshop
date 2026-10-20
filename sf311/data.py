"""The bundled one-week snapshot of San Francisco 311 cases.

Each row is one report a resident filed with the city: graffiti, a broken
streetlight, a blocked sidewalk. The snapshot covers October 12 to 18, 2026.
See data/README.md for the source and license.
"""

import csv
import gzip
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "311_cases.csv.gz"


@dataclass(frozen=True)
class Request:
    request_id: str
    opened: datetime
    closed: datetime | None
    status: str
    service: str
    subtype: str
    agency: str
    neighborhood: str
    """One of the city's 41 official analysis neighborhoods, or "" when unknown."""
    local_name: str
    """The name people use for the area, such as "Lower Nob Hill". It can span several official neighborhoods."""
    address: str
    source: str

    @property
    def hours_to_close(self) -> float | None:
        if self.closed is None:
            return None
        return (self.closed - self.opened).total_seconds() / 3600

    def as_dict(self) -> dict:
        row = asdict(self)
        row["opened"] = self.opened.isoformat()
        row["closed"] = self.closed.isoformat() if self.closed else None
        return row


def _parse_time(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _load() -> list[Request]:
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as handle:
        return [
            Request(
                request_id=row["service_request_id"],
                opened=_parse_time(row["requested_datetime"]),
                closed=_parse_time(row["closed_date"]),
                status=row["status_description"],
                service=row["service_name"],
                subtype=row["service_subtype"],
                agency=row["agency_responsible"],
                neighborhood=row["analysis_neighborhood"],
                local_name=row["neighborhoods_sffind_boundaries"],
                address=row["address"],
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]


REQUESTS: list[Request] = _load()
BY_ID: dict[str, Request] = {request.request_id: request for request in REQUESTS}
SERVICES: list[str] = sorted({request.service for request in REQUESTS})
NEIGHBORHOODS: list[str] = sorted({request.neighborhood for request in REQUESTS if request.neighborhood})
LOCAL_NAMES: list[str] = sorted({request.local_name for request in REQUESTS if request.local_name})


def closest(name: str, choices: list[str], count: int = 3) -> list[str]:
    """Return the choices that look most like `name`, for "did you mean" messages."""
    by_lower = {choice.lower(): choice for choice in choices}
    matches = get_close_matches(name.lower(), list(by_lower), n=count, cutoff=0.4)
    return [by_lower[match] for match in matches]
