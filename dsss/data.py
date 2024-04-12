from typing import TYPE_CHECKING, List, Mapping, Tuple

import sdmx
from sdmx.format import MediaType
from starlette.convertors import Convertor, register_url_convertor
from starlette.routing import Route

from . import storage
from .common import (
    SDMXResponse,
    add_footer_text,
    handle_media_type,
    handle_query_params,
    not_implemented_path,
)

if TYPE_CHECKING:
    import starlette.requests

    import dsss.config

NOT_IMPLEMENTED_QUERY = {
    "detail",
    "dimension_at_observation",
    "end_period",
    "first_n_observations",
    "include_history",
    "last_n_observations",
    "start_period",
    "updated_after",
}


class FlowRefConvertor(Convertor):
    regex = ".*"
    defaults = [None, "all", "latest"]

    def convert(self, value: str) -> Tuple[str, str, str]:
        result = value.split(",")

        if len(result) > 3:
            raise ValueError(f"flow_ref={value}")

        return tuple(result + self.defaults[len(result) :])  # type: ignore [return-value]

    def to_string(self, value: Tuple[str, str, str]) -> str:
        return ",".join(value)


def register_convertors():
    register_url_convertor("flow_ref", FlowRefConvertor())


def get_routes():
    register_convertors()

    return [
        # SDMX-REST 1.5.0 / SDMX 2.1
        Route("/data/{flow_ref:flow_ref}", handle),
        Route("/data/{flow_ref:flow_ref}/{key}", handle),
        Route("/data/{flow_ref:flow_ref}/{key}/{provider_ref}", handle),
        # TODO Add SDMX-REST 2.1.0 / SDMX 3.0.0 paths
    ]


async def handle(request: "starlette.requests.Request"):
    media_type = handle_media_type(
        [MediaType("genericdata", "xml", "2.1")], request.headers.get("Accept")
    )

    qp = handle_query_params(
        sdmx.rest.v21.URL,
        "start_period end_period updated_after first_n_observations "
        "last_n_observations dimension_at_observation detail_d include_history",
        request.query_params,
        not_implemented=NOT_IMPLEMENTED_QUERY,
    )

    msg = get_data(request.app.state.config, request.path_params, qp)

    return SDMXResponse(msg, media_type=media_type)


def get_data(config: "dsss.config.Config", path_params: Mapping, query_params: Mapping):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}:{flow_id}-structure.xml`
    """
    footer_text: List[str] = []

    # Unpack path parameters
    resource = "data"
    agency_id, flow_id, version = path_params["flow_ref"]
    key = path_params.get("key", None)
    provider_ref = path_params.get("provider_ref", None)

    # ‘Repository’ of *all* data for this flow
    repo, cache_key = storage.get(
        config,
        f"{agency_id}:{flow_id}-{resource}.xml",
        (resource, agency_id, flow_id, version, key, provider_ref, query_params),
    )

    if not cache_key:
        add_footer_text(repo, footer_text)
        return repo

    # Cache miss; file was freshly loaded and must be filtered

    # Filter

    # Warn about filtering features not implemented yet
    footer_text.extend(
        not_implemented_path(
            dict(version="latest", key="all", provider_ref="all"),
            version=version,
            key=key,
            provider_ref=provider_ref,
        )
    )
    # TODO Attach log messages about not implemented query parameters

    add_footer_text(repo, footer_text)

    return repo
