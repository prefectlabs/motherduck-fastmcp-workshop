"""Exercise 3: addresses never reach the model, and every lookup records who asked."""

import logging

import reference
import sf311.kit

NUMBERED = [r for r in reference.REQUESTS if reference.HOUSE_NUMBER.match(r.address)]


async def test_search_results_show_addresses_only_to_the_block(client):
    result = await client.call_tool("search_requests", {"service": "Encampment", "limit": 50})
    by_id = {r.request_id: r for r in reference.REQUESTS}
    for row in result.data:
        original = by_id[row["request_id"]].address
        assert row["address"] == reference.mask_address(original), f"{original!r} was not masked"


async def test_get_request_shows_the_address_only_to_the_block(client):
    request = NUMBERED[0]
    result = await client.call_tool("get_request", {"request_id": request.request_id})
    assert result.data["address"] == reference.mask_address(request.address)


async def test_get_request_logs_the_verified_caller(client, monkeypatch, caplog):
    monkeypatch.setattr(sf311.kit, "get_http_headers", lambda: {sf311.kit.ACTOR_EMAIL_HEADER: "maria@example.com"})
    caplog.set_level(logging.INFO)
    await client.call_tool("get_request", {"request_id": NUMBERED[1].request_id})
    assert "maria@example.com" in caplog.text


async def test_get_request_works_locally_without_the_identity_header(client, monkeypatch):
    monkeypatch.setattr(sf311.kit, "get_http_headers", lambda: {})
    result = await client.call_tool("get_request", {"request_id": NUMBERED[2].request_id})
    assert result.data["request_id"] == NUMBERED[2].request_id
