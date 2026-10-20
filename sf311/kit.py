"""Small helpers for running on FastMCP Gateway."""

from dataclasses import dataclass

from fastmcp import Context
from fastmcp.server.dependencies import get_http_headers
from mcp.types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult

ACTOR_EMAIL_HEADER = "horizon-actor-email"
"""The header FastMCP Gateway sets to the verified caller's email.

The gateway deletes any copy the client sends, so your code can trust it.
It is absent when the server runs locally.
"""


def caller_email() -> str | None:
    """Return the verified caller's email, or None when running locally."""
    return get_http_headers().get(ACTOR_EMAIL_HEADER)


def ask_choice(key: str, message: str, options: list[str]) -> InputRequiredResult:
    """Ask the user to pick one option.

    Return this from a tool. The client shows a form, then calls the same tool
    again with the answer, which `read_choice` reads. The tool saves nothing
    between the two calls, so any copy of the server can handle the retry.
    """
    form = ElicitRequestFormParams(
        message=message,
        requested_schema={
            "type": "object",
            "properties": {"choice": {"type": "string", "enum": options}},
            "required": ["choice"],
        },
    )
    return InputRequiredResult(
        result_type="input_required",
        input_requests={key: ElicitRequest(method="elicitation/create", params=form)},
    )


@dataclass(frozen=True)
class Choice:
    accepted: bool
    """False when the user declined or cancelled the form."""
    value: str | None


def read_choice(ctx: Context, key: str) -> Choice | None:
    """Return the user's answer to `ask_choice(key, ...)`, or None before they have been asked."""
    responses = ctx.input_responses
    if not responses or key not in responses:
        return None
    answer = responses[key]
    if answer.action != "accept":
        return Choice(accepted=False, value=None)
    return Choice(accepted=True, value=answer.content["choice"])
