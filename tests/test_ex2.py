"""Exercise 2: tools that answer questions about the 311 data."""

import pytest
from fastmcp.exceptions import ToolError

import reference

REQUIRED_TOOLS = ["search_requests", "count_requests", "median_close_hours", "get_request"]


async def test_required_tools_exist_with_docstrings_and_read_only_hints(client):
    tools = {tool.name: tool for tool in await client.list_tools()}
    for name in REQUIRED_TOOLS:
        assert name in tools, f"Missing tool {name}"
        assert tools[name].description, f"{name} needs a docstring the model can read"
        assert tools[name].annotations and tools[name].annotations.read_only_hint, f"{name} needs readOnlyHint"


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"service": "Graffiti Public"},
        {"service": "Encampment", "neighborhood": "Mission"},
        {"service": "Streetlights", "group_by": "neighborhood"},
        {"service": "Graffiti Public", "group_by": "agency"},
        {"service": "Parking Enforcement", "group_by": "weekday"},
        {"service": "Street and Sidewalk Cleaning", "group_by": "source"},
        {"neighborhood": "Tenderloin", "group_by": "service"},
        {"group_by": "status"},
    ],
)
async def test_count_requests_matches_the_data(client, arguments):
    result = await client.call_tool("count_requests", arguments)
    assert result.data == reference.count_requests(**arguments)


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"service": "Streetlights"},
        {"service": "Graffiti Public", "group_by": "neighborhood"},
        {"service": "Encampment", "group_by": "agency"},
    ],
)
async def test_median_close_hours_matches_the_data(client, arguments):
    result = await client.call_tool("median_close_hours", arguments)
    expected = reference.median_close_hours(**arguments)
    if isinstance(expected, dict):
        assert result.data.keys() == expected.keys()
        for group, hours in expected.items():
            assert result.data[group] == pytest.approx(hours, abs=0.1)
    else:
        assert result.data == pytest.approx(expected, abs=0.1)


async def test_search_requests_filters_and_stays_small(client):
    result = await client.call_tool("search_requests", {"service": "Encampment", "neighborhood": "Mission", "limit": 50})
    assert 0 < len(result.data) <= reference.MAX_ROWS
    for row in result.data:
        assert row["service"] == "Encampment"
        assert row["neighborhood"] == "Mission"


async def test_search_requests_never_returns_more_than_50_rows(client):
    try:
        result = await client.call_tool("search_requests", {"limit": 500})
    except ToolError:
        return
    assert len(result.data) <= reference.MAX_ROWS


async def test_unknown_neighborhood_error_suggests_a_real_one(client):
    with pytest.raises(ToolError, match="Tenderloin"):
        await client.call_tool("count_requests", {"neighborhood": "Tendarloin"})


async def test_get_request_returns_that_request(client):
    request = reference.REQUESTS[100]
    result = await client.call_tool("get_request", {"request_id": request.request_id})
    assert result.data["request_id"] == request.request_id
    assert result.data["service"] == request.service
