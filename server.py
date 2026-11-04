"""Your MCP server for San Francisco 311 data.

FastMCP Gateway runs this file. Its entrypoint setting is `server.py:mcp`.
"""

from collections import Counter, defaultdict
from statistics import median
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from sf311.data import BY_ID, LOCAL_NAMES, NEIGHBORHOODS, REQUESTS, SERVICES, closest

MAX_ROWS = 50
MIN_CLOSED_FOR_MEDIAN = 10

mcp = FastMCP("sf-311")


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


def _check(value: str | None, choices: list[str], kind: str) -> None:
    if value is not None and value not in choices:
        suggestions = closest(value, choices)
        hint = f"Did you mean: {', '.join(suggestions)}?" if suggestions else "Call dataset_info for valid names."
        raise ToolError(f"Unknown {kind} {value!r}. {hint}")


def _matching(service=None, neighborhood=None, status=None) -> list:
    _check(service, SERVICES, "service")
    _check(neighborhood, NEIGHBORHOODS, "neighborhood")
    return [
        r
        for r in REQUESTS
        if (service is None or r.service == service)
        and (neighborhood is None or r.neighborhood == neighborhood)
        and (status is None or r.status == status)
    ]


@mcp.tool(annotations={"readOnlyHint": True})
def search_requests(
    service: str | None = None,
    neighborhood: str | None = None,
    status: Literal["Open", "Closed"] | None = None,
    limit: int = 20,
) -> list[dict]:
    """List individual 311 requests, newest first, optionally filtered.

    Use this to look at example requests (address, subtype, status). Returns
    at most 50 rows with every field of a request. Do NOT use it to count or
    rank: use count_requests. For timing, use median_close_hours. To fetch one
    known request, use get_request. Service and neighborhood must match
    dataset_info exactly.
    """
    if not 1 <= limit <= MAX_ROWS:
        raise ToolError(f"limit must be between 1 and {MAX_ROWS}; try limit={MAX_ROWS}.")
    rows = sorted(_matching(service, neighborhood, status), key=lambda r: r.opened, reverse=True)
    return [r.as_dict() for r in rows[:limit]]


@mcp.tool(annotations={"readOnlyHint": True})
def count_requests(
    service: str | None = None,
    neighborhood: str | None = None,
    group_by: Literal["neighborhood", "service", "agency", "source", "weekday", "status"] | None = None,
) -> int | dict[str, int]:
    """Count 311 requests, optionally filtered and grouped.

    Without group_by, returns one number. With group_by, returns a dict of
    group to count, largest first, at most 50 groups. Use this for "how many",
    "which neighborhood has the most", or "what is the top service in X"
    (filter by neighborhood, group_by service). To see actual requests, use
    search_requests; for how long requests take, use median_close_hours.
    Service and neighborhood must match dataset_info exactly.
    """
    rows = _matching(service, neighborhood)
    if group_by is None:
        return len(rows)
    key = GROUPS[group_by]
    counts = Counter(key(r) for r in rows if key(r))
    pairs = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return dict(pairs[:MAX_ROWS])


@mcp.tool(annotations={"readOnlyHint": True})
def median_close_hours(
    service: str | None = None,
    group_by: Literal["neighborhood", "agency"] | None = None,
) -> float | None | dict[str, float]:
    """Median hours from opened to closed, over closed requests only.

    Without group_by, returns one number (null if nothing closed). With
    group_by, returns a dict of group to hours, fastest first, omitting groups
    with fewer than 10 closed requests. Use this for "how fast" questions. For
    volumes use count_requests; for example requests use search_requests.
    """
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


@mcp.tool(annotations={"readOnlyHint": True})
def get_request(request_id: str) -> dict:
    """Fetch one 311 request by its request_id, with all fields.

    Use this when you already have an id (for example from search_requests).
    To find requests by service, neighborhood or status, use search_requests.
    """
    request = BY_ID.get(request_id)
    if request is None:
        raise ToolError(f"No request with id {request_id!r}. Use search_requests to find valid request_ids.")
    return request.as_dict()


COLUMNS = {
    "request_id": "Unique id of the request. Pass it to get_request.",
    "opened": "ISO timestamp when the request was filed.",
    "closed": "ISO timestamp when it was closed, or null while still open.",
    "status": "Open or Closed.",
    "service": "Kind of request, such as Graffiti Public. Exact names are listed by dataset_info.",
    "subtype": "A finer category within the service.",
    "agency": "City agency responsible for the request.",
    "neighborhood": "One of the 41 official analysis neighborhoods, or empty when unknown. Filters use this field.",
    "local_name": "The name people use for the area, such as Lower Nob Hill. It can span several official neighborhoods. No tool filters on it yet.",
    "address": "Street address of the request.",
    "source": "How the request was filed, such as phone or mobile app.",
}


@mcp.resource(
    "sf311://columns",
    mime_type="application/json",
    annotations={"readOnlyHint": True},
)
def columns() -> dict[str, str]:
    """What each field of a 311 request means. Rows from search_requests and get_request have these keys."""
    return COLUMNS


if __name__ == "__main__":
    mcp.run()
