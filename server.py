"""Your MCP server for San Francisco 311 data.

FastMCP Gateway runs this file. Its entrypoint setting is `server.py:mcp`.
"""

import logging
import re
from collections import Counter, defaultdict
from statistics import median
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from sf311.data import BY_ID, LOCAL_NAMES, NEIGHBORHOODS, REQUESTS, SERVICES, Request, closest
from sf311.kit import caller_email

mcp = FastMCP("sf-311")
log = logging.getLogger("sf311.server")

HOUSE_NUMBER = re.compile(r"^(\d+)\s+([^,]+)")


def _mask_address(address: str | None) -> str | None:
    """Reduce a street address to its block; leave addresses without a house number alone."""
    match = HOUSE_NUMBER.match(address or "")
    if not match:
        return address
    block = int(match.group(1)) // 100 * 100
    return f"{block} block of {match.group(2).strip()}"


def _public(request: Request) -> dict:
    """The record a tool may return: the address is masked to the block."""
    row = request.as_dict()
    row["address"] = _mask_address(row.get("address"))
    return row


@mcp.tool(annotations={"readOnlyHint": True})
def dataset_info() -> dict:
    """Describe the 311 dataset this server answers questions about.

    Call this first to learn the date range and the exact service and
    neighborhood names that other tools accept.
    """
    return {
        "description": "San Francisco 311 service requests filed in one week.",
        "first_opened": min(request.opened for request in REQUESTS).isoformat(),
        "last_opened": max(request.opened for request in REQUESTS).isoformat(),
        "requests": len(REQUESTS),
        "services": SERVICES,
        "neighborhoods": NEIGHBORHOODS,
        "local_neighborhood_names": len(LOCAL_NAMES),
    }


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


def _check_name(kind: str, value: str | None, choices: list[str]) -> None:
    if value is None or value in choices:
        return
    suggestions = closest(value, choices)
    hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    raise ToolError(f"Unknown {kind} {value!r}.{hint} Call dataset_info for the exact names.")


def _matching(service=None, neighborhood=None, status=None) -> list[Request]:
    _check_name("service", service, SERVICES)
    _check_name("neighborhood", neighborhood, NEIGHBORHOODS)
    if status is not None and status not in ("Open", "Closed"):
        raise ToolError(f"Unknown status {status!r}. Use 'Open' or 'Closed'.")
    return [
        r
        for r in REQUESTS
        if (service is None or r.service == service)
        and (neighborhood is None or r.neighborhood == neighborhood)
        and (status is None or r.status == status)
    ]


def _check_group(group_by: str | None, allowed) -> None:
    if group_by is not None and group_by not in allowed:
        raise ToolError(f"Unknown group_by {group_by!r}. Use one of: {', '.join(allowed)}.")


@mcp.tool(annotations={"readOnlyHint": True})
def count_requests(
    service: str | None = None,
    neighborhood: str | None = None,
    group_by: Literal["neighborhood", "service", "agency", "source", "weekday", "status"] | None = None,
) -> int | dict[str, int]:
    """Count this week's 311 requests, optionally filtered by service and neighborhood.

    Without group_by, returns a single number. With group_by, returns a dict of
    group -> count, largest first, at most 50 groups. Use this for any "how many"
    or "which has the most" question instead of fetching rows with search_requests.
    Service and neighborhood must be exact names from dataset_info.
    """
    _check_group(group_by, GROUPS)
    rows = _matching(service, neighborhood)
    if group_by is None:
        return len(rows)
    key = GROUPS[group_by]
    counts = Counter(key(r) for r in rows if key(r))
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:MAX_ROWS])


@mcp.tool(annotations={"readOnlyHint": True})
def median_close_hours(
    service: str | None = None,
    group_by: Literal["neighborhood", "agency"] | None = None,
) -> float | None | dict[str, float]:
    """Median hours from opened to closed for closed requests, rounded to 0.1.

    Without group_by, returns one number (None if nothing has closed). With
    group_by, returns a dict of group -> median hours, fastest first, omitting
    groups with fewer than 10 closed requests. Use this for "how fast" questions;
    use count_requests for volumes.
    """
    _check_group(group_by, MEDIAN_GROUPS)
    rows = [r for r in _matching(service) if r.hours_to_close is not None]
    if group_by is None:
        return round(median(r.hours_to_close for r in rows), 1) if rows else None
    key = GROUPS[group_by]
    hours = defaultdict(list)
    for r in rows:
        if key(r):
            hours[key(r)].append(r.hours_to_close)
    medians = {g: round(median(v), 1) for g, v in hours.items() if len(v) >= MIN_CLOSED_FOR_MEDIAN}
    return dict(sorted(medians.items(), key=lambda item: (item[1], item[0]))[:MAX_ROWS])


def _range(hours: list[float]) -> dict:
    return {
        "closed": len(hours),
        "min_hours": round(min(hours), 1),
        "median_hours": round(median(hours), 1),
        "max_hours": round(max(hours), 1),
    }


@mcp.tool(annotations={"readOnlyHint": True})
def close_hours_range(
    service: str | None = None,
    group_by: Literal["neighborhood", "agency"] | None = None,
) -> dict:
    """Fastest, median and slowest hours from opened to closed, for closed requests.

    Without group_by, returns {closed, min_hours, median_hours, max_hours}
    (hours rounded to 0.1; closed is 0 and the hours are None if nothing has
    closed). Use it for "longest/shortest time any request took to close".
    With group_by, returns group -> that same dict, slowest max first, at most
    50 groups; use it to compare the fastest and slowest neighborhoods or agencies.
    For volumes use count_requests; for just a median, median_close_hours.
    """
    _check_group(group_by, MEDIAN_GROUPS)
    rows = [r for r in _matching(service) if r.hours_to_close is not None]
    if group_by is None:
        if not rows:
            return {"closed": 0, "min_hours": None, "median_hours": None, "max_hours": None}
        return _range([r.hours_to_close for r in rows])
    key = GROUPS[group_by]
    hours = defaultdict(list)
    for r in rows:
        if key(r):
            hours[key(r)].append(r.hours_to_close)
    ranges = {g: _range(v) for g, v in hours.items()}
    ordered = sorted(ranges.items(), key=lambda item: (-item[1]["max_hours"], item[0]))
    return dict(ordered[:MAX_ROWS])


@mcp.tool(annotations={"readOnlyHint": True})
def search_requests(
    service: str | None = None,
    neighborhood: str | None = None,
    status: Literal["Open", "Closed"] | None = None,
    limit: int = 20,
) -> list[dict]:
    """List individual 311 requests matching the filters, newest first.

    Returns up to `limit` (1-50) request records. Use this to see examples or
    details; do not use it to count, since results are capped. Use
    count_requests for totals and get_request for one known request_id.
    Addresses are shown only to the block (e.g. "900 block of HARRISON ST").
    """
    if not 1 <= limit <= MAX_ROWS:
        raise ToolError(f"limit must be between 1 and {MAX_ROWS}. For totals, use count_requests.")
    rows = sorted(_matching(service, neighborhood, status), key=lambda r: r.opened, reverse=True)
    return [_public(r) for r in rows[:limit]]


@mcp.tool(annotations={"readOnlyHint": True})
def get_request(request_id: str) -> dict:
    """Return the full record for one 311 request by its request_id.

    Use this when you already have an ID, e.g. from search_requests. The
    address is shown only to the block (e.g. "900 block of HARRISON ST").
    """
    log.info("get_request request_id=%s caller=%s", request_id, caller_email() or "local")
    request = BY_ID.get(request_id.strip())
    if request is None:
        raise ToolError(f"No request with id {request_id!r}. Use search_requests to find valid IDs.")
    return _public(request)


if __name__ == "__main__":
    mcp.run()
