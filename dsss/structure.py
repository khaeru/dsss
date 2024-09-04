"""Structure query endpoints."""

from itertools import product
from typing import TYPE_CHECKING, List, Mapping

import sdmx
from sdmx.format import MediaType
from sdmx.model import v30
from sdmx.model.v21 import get_class
from sdmx.rest.common import Resource
from starlette.convertors import Convertor, register_url_convertor
from starlette.routing import Route

from .common import (
    SDMXResponse,
    add_footer_text,
    gen_error_message,
    handle_media_type,
    handle_query_params,
)

if TYPE_CHECKING:
    import starlette.requests

    import dsss.config

NOT_IMPLEMENTED_QUERY = {"detail", "references"}

#: SDMX 3.0 IM classes not yet handled by :mod:`sdmx.writer.xml`.
NOT_IMPLEMENTED_WRITE_SDMX_ML_3_0 = (
    v30.GeoGridCodelist,
    v30.GeographicCodelist,
    v30.Dataflow,
    v30.DataStructureDefinition,
)


class BaseResourceConvertor(Convertor):
    """Convert a string path fragment to a :class:`sdmx.Resource` enum value."""

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
    resource_id = path_params.get("resource_id")
    version = path_params.get("version")

    # sdmx.model class for the resource
    klass = get_class(resource)

    if klass is None:
        footer_text.append(f"resource={resource!r}")
        return gen_error_message(501, "\n\n".join(footer_text))

    message = sdmx.message.StructureMessage()

    for urn in config.store.list(
        klass,
        maintainer=None if agency_id == "ALL" else agency_id,
        id=None if resource_id in ("all", None) else resource_id,
        # TODO Actually honour "+"/"latest"
        version=None if version in ("+", "latest", None) else version,
    ):
        obj = config.store.get(urn)

        if isinstance(obj, NOT_IMPLEMENTED_WRITE_SDMX_ML_3_0):
            footer_text.append(f"Omit unsupported {obj.__class__} {urn}")
            continue

        message.objects(type(obj))[urn.split("=")[-1]] = obj

    N = len(list(message.iter_objects()))
    if N == 0:
        return gen_error_message(404, "\n\n".join(footer_text))

    # TODO Attach log messages about not implemented query parameters
    add_footer_text(message, footer_text)

    return message


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
