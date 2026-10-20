# Instructions for coding agents

This repo is a workshop.
A person is directing you through four exercises in `exercises/`.
Each exercise has a brief, rules, and a test file that decides when it is done.

## The project

- `server.py` is the MCP server that FastMCP Gateway deploys. Its entrypoint is `server.py:mcp`. Keep that name and that object.
- `sf311/data.py` loads the bundled 311 snapshot. Use `REQUESTS`, `BY_ID`, `SERVICES`, `NEIGHBORHOODS`, `LOCAL_NAMES`, and `closest()`. Do not read the CSV yourself.
- `sf311/kit.py` has the helpers for running on FastMCP Gateway: `caller_email()`, `ask_choice()`, and `read_choice()`.
- `tests/` holds the acceptance tests. Do not edit them. Do not edit `tests/reference.py`.
- `solutions/` holds a finished server for each exercise. Do not copy from it unless the person asks you to.

## Rules

- FastMCP is pinned to 4.1.1. Use the FastMCP 4 docs at https://gofastmcp.com. Older examples online use APIs that changed.
- Mark every tool that only reads data with `annotations={"readOnlyHint": True}`.
- Write each tool's docstring for the model that calls it: say what it returns, and when to use a different tool.
- Return at most 50 rows from any tool.
- Raise `fastmcp.exceptions.ToolError` for bad input, with a message that says what to try instead.
- Read the caller with `caller_email()` from `sf311.kit`. It returns None when the server runs locally.
- To ask the user a question, return `ask_choice(...)` from the tool and read the answer with `read_choice(ctx, key)` when the client calls the tool again.
  Never call `ctx.elicit()`: it fails on FastMCP Gateway.
  Never pass `request_state`: the retry can reach a different copy of the server, which cannot read it.
- Add no new dependencies.

## Before every push

Run the tests for the current exercise and fix every failure:

```bash
uv run pytest tests/test_ex2.py
```

A push to the default branch deploys the server. A failing build leaves the previous deployment live.
