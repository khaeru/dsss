from itertools import product
from typing import TYPE_CHECKING, List, Mapping

import sdmx
from sdmx.format import MediaType
from sdmx.rest.common import Resource
from starlette.convertors import Convertor, register_url_convertor
from starlette.responses import Response
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

NOT_IMPLEMENTED_QUERY = {"detail", "references"}


class BaseResourceConvertor(Convertor):
    def convert(self, value: str) -> Resource:
        return Resource[value]

    def to_string(self, value: Resource) -> str:
        return value.name


def register_convertors():
    expr = "|".join([r.name for r in Resource if r != Resource.data])

    StructureResourceConvertor = type(
        "StructureResourceConvertor", (BaseResourceConvertor,), {"regex": expr}
    )
    register_url_convertor("resource_type", StructureResourceConvertor())


def get_routes():
    register_convertors()

    bases = [
        "/structure/{resource_type:resource_type}",  # SDMX-REST 2.1.0 / SDMX 3.0.0
        "/{resource_type:resource_type}",  # SDMX-REST 1.5.0 / SDMX 2.1
    ]
    paths = [
        "/{agency_id}",
        "/{agency_id}/{resource_id}",
        "/{agency_id}/{resource_id}/{version}",
        "/{agency_id}/{resource_id}/{version}/{item_id}",
    ]
    for base, path in product(bases, paths):
        yield Route(f"{base}{path}", handle)


def get_structures(
    config: "dsss.config.Config", path_params: Mapping, query_params: Mapping
):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}-structure.xml`.
    """
    footer_text: List[str] = []

    resource = path_params["resource_type"]
    agency_id = path_params["agency_id"]
    resource_id = path_params.get("resource_id", "all")
    version = path_params.get("version", "all")
    item_id = "all"

    if agency_id == "all":
        # Determine the list of all providers being served
        agency_ids = list(
            map(lambda p: p.name.split("-")[0], storage.glob("*-structure.xml"))
        )

        if len(agency_ids) > 1:
            raise NotImplementedError("Combine structures from ≥2 providers")

        # Use the first provider
        agency_id = agency_ids[0]

    # ‘Repository’ of *all* structures
    repo, cache_key = storage.get(
        config,
        f"{agency_id}-structure.xml",
        (resource, agency_id, resource_id, version, item_id, query_params),
    )

    if not cache_key:
        add_footer_text(repo, footer_text)
        return repo

    # Cache miss; file was freshly loaded and must be filtered

    # Filtered message
    msg = sdmx.message.StructureMessage()

    # sdmx.model class for the resource
    cls = sdmx.model.v21.get_class(resource)

    if cls is None:
        footer_text.append(f"resource={repr(resource)}")
        return Response(footer_text, status_code=501)

    # Source and target collections
    collection = repo.objects(cls)
    target = msg.objects(cls)

    if collection is None:
        return Response(footer_text, status_code=501)

    # Filter

    # Warn about filtering features not implemented yet
    footer_text.extend(not_implemented_path(dict(version="latest"), version=version))
    # TODO Attach log messages about not implemented query parameters

    if resource_id == "all":
        # Copy all object
        target.update(collection)
    else:
        try:
            # Copy a single object
            getattr(msg, resource)[resource_id] = collection[resource_id]
        except KeyError:
            # Not found
            return Response(footer_text, status_code=404)

    add_footer_text(msg, footer_text)

    return msg


async def handle(request: "starlette.requests.Request"):
    media_type = handle_media_type(
        [MediaType("structure", "xml", "2.1")], request.headers.get("Accept")
    )

    qp = handle_query_params(
        sdmx.rest.v21.URL,
        "detail_s references_s",
        request.query_params,
        not_implemented=NOT_IMPLEMENTED_QUERY,
    )
    msg = get_structures(request.app.state.config, request.path_params, qp)

    return SDMXResponse(message=msg, media_type=media_type)
