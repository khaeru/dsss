"""Schema query endpoints."""

from typing import TYPE_CHECKING

from starlette.routing import Route

from .common import gen_error_response

if TYPE_CHECKING:
    import starlette.requests
    import starlette.responses


def get_routes():
    return [
        Route("/schema", handle),
    ]


async def handle(
    request: "starlette.requests.Request",
) -> "starlette.responses.Response":
    return gen_error_response(501)
