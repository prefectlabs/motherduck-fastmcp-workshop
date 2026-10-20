"""Exercise 4: a tool that asks which neighborhood you mean."""

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

import reference

AMBIGUOUS = "Lower Nob Hill"
IN_AREA = [r for r in reference.REQUESTS if r.local_name == AMBIGUOUS]


def answering(choice: str | None, asked: list):
    async def handler(message, response_type, params, context):
        asked.append(params.requested_schema["properties"]["choice"]["enum"])
        if choice is None:
            return ElicitResult(action="decline")
        return {"choice": choice}

    return handler


async def test_an_official_name_is_counted_without_asking(server_module):
    asked = []
    async with Client(server_module.mcp, elicitation_handler=answering("Tenderloin", asked)) as client:
        result = await client.call_tool("count_in_neighborhood", {"name": "Mission"})
    assert result.data == reference.count_requests(neighborhood="Mission")
    assert asked == []


async def test_an_ambiguous_local_name_asks_and_counts_the_chosen_part(server_module):
    asked = []
    async with Client(server_module.mcp, elicitation_handler=answering("Tenderloin", asked)) as client:
        result = await client.call_tool("count_in_neighborhood", {"name": AMBIGUOUS})
    assert len(asked) == 1, "The tool should ask exactly once"
    assert {"Nob Hill", "Tenderloin"} <= set(asked[0])
    assert result.data == sum(1 for r in IN_AREA if r.neighborhood == "Tenderloin")


async def test_boundary_argument_skips_the_question(server_module):
    asked = []
    async with Client(server_module.mcp, elicitation_handler=answering("Nob Hill", asked)) as client:
        result = await client.call_tool("count_in_neighborhood", {"name": AMBIGUOUS, "boundary": "Tenderloin"})
    assert asked == []
    assert result.data == sum(1 for r in IN_AREA if r.neighborhood == "Tenderloin")


async def test_declining_the_question_returns_a_message(server_module):
    asked = []
    async with Client(server_module.mcp, elicitation_handler=answering(None, asked)) as client:
        result = await client.call_tool("count_in_neighborhood", {"name": AMBIGUOUS})
    assert isinstance(result.data, str)


def test_uses_the_retry_pattern_that_works_on_hosted_servers(server_source):
    assert "ctx.elicit(" not in server_source, (
        "ctx.elicit() fails on FastMCP Gateway. Return ask_choice(...) and read the answer with read_choice(ctx, ...)."
    )
    assert "request_state=" not in server_source, (
        "Saving requestState fails when the retry reaches another copy of the server. Re-derive what you need instead."
    )
