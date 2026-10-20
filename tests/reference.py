"""The expected answers that the exercise tests compare against.

The tests import these functions to compute the right answer for any input.
The room server uses the same rules to check challenge answers.
"""

import re
from collections import Counter, defaultdict
from statistics import median

from sf311.data import REQUESTS, Request

GROUPS = {
    "neighborhood": lambda r: r.neighborhood,
    "service": lambda r: r.service,
    "agency": lambda r: r.agency,
    "source": lambda r: r.source,
    "weekday": lambda r: r.opened.strftime("%A"),
    "status": lambda r: r.status,
}
MEDIAN_GROUPS = ("neighborhood", "agency")
MIN_CLOSED_FOR_MEDIAN = 10
MAX_ROWS = 50


def matching(service: str | None = None, neighborhood: str | None = None, status: str | None = None) -> list[Request]:
    return [
        r
        for r in REQUESTS
        if (service is None or r.service == service)
        and (neighborhood is None or r.neighborhood == neighborhood)
        and (status is None or r.status == status)
    ]


def ranked(counter: Counter) -> dict[str, int]:
    pairs = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return dict(pairs[:MAX_ROWS])


def count_requests(service=None, neighborhood=None, group_by=None) -> int | dict[str, int]:
    rows = matching(service, neighborhood)
    if group_by is None:
        return len(rows)
    key = GROUPS[group_by]
    return ranked(Counter(key(r) for r in rows if key(r)))


def median_close_hours(service=None, group_by=None) -> float | None | dict[str, float]:
    rows = [r for r in matching(service) if r.hours_to_close is not None]
    if group_by is None:
        return round(median(r.hours_to_close for r in rows), 1) if rows else None
    key = GROUPS[group_by]
    hours = defaultdict(list)
    for r in rows:
        if key(r):
            hours[key(r)].append(r.hours_to_close)
    medians = {group: round(median(values), 1) for group, values in hours.items() if len(values) >= MIN_CLOSED_FOR_MEDIAN}
    return dict(sorted(medians.items(), key=lambda item: (item[1], item[0]))[:MAX_ROWS])


HOUSE_NUMBER = re.compile(r"^(\d+)\s+([^,]+)")


def mask_address(address: str) -> str:
    """Turn "994 HARRISON ST, SAN FRANCISCO, ..." into "900 block of HARRISON ST"."""
    match = HOUSE_NUMBER.match(address)
    if not match:
        return address
    block = int(match.group(1)) // 100 * 100
    return f"{block} block of {match.group(2).strip()}"
