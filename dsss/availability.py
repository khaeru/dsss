from typing import TYPE_CHECKING

import sdmx.rest.v30
from starlette.responses import Response
from starlette.routing import Route

from .common import handle_query_params

if TYPE_CHECKING:
    import starlette.requests

NOT_IMPLEMENTED_QUERY = {"c", "mode", "references_a", "updated_after"}


def get_routes():
    return [
        Route(
            "/availability/{context_d}/{agency_id}/{resource_id}/{version}/{key}/"
            "{component_id}",
            handle,
        ),
    ]


async def handle(request: "starlette.requests.Request"):
    qp = handle_query_params(
        sdmx.rest.v30.URL,
        "c mode references_a updated_after",
        request.query_params,
        not_implemented=NOT_IMPLEMENTED_QUERY,
    )
    del qp

    return Response(status_code=501)
