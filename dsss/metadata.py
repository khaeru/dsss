from typing import TYPE_CHECKING

from starlette.responses import Response
from starlette.routing import Route

if TYPE_CHECKING:
    import starlette.requests


def get_routes():
    return [
        Route("/metadata", handle),
    ]


async def handle(request: "starlette.requests.Request"):
    return Response(status_code=501)
