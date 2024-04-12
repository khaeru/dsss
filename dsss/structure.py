from collections import ChainMap
from itertools import product
from typing import TYPE_CHECKING, Mapping

import sdmx
from sdmx.rest.common import Resource
from starlette.convertors import Convertor, register_url_convertor
from starlette.responses import Response
from starlette.routing import Route

from . import cache, storage
from .util import (
    add_footer_text,
    finalize_message,
    not_implemented_options,
    not_implemented_path,
)

if TYPE_CHECKING:
    import starlette.requests

    import dsss.config


class BaseResourceConvertor(Convertor):
    def convert(self, value: str) -> Resource:
        return Resource[value]

    def to_string(self, value: Resource) -> str:
        return value.name


def get_routes():
    StructureResourceConvertor = type(
        "StructureResourceConvertor",
        (BaseResourceConvertor,),
        {"regex": "agencyscheme|codelist|reportingtaxonomy"},
    )
    register_url_convertor("sdmx_resource_structure", StructureResourceConvertor())

    bases = [
        "/structure/{resource_type:sdmx_resource_structure}",  # SDMX-REST 2.1.0
        "/{resource_type:sdmx_resource_structure}",  # SDMX-REST 1.5.0 / SDMX 2.1
    ]
    paths = [
        "/{agency_id}",
        "/{agency_id}/{resource_id}",
        "/{agency_id}/{resource_id}/{version}",
        "/{agency_id}/{resource_id}/{version}/{item_id}",
    ]
    for base, path in product(bases, paths):
        yield Route(f"{base}{path}", handle)


def get_structures(config: "dsss.config.Config", params: Mapping):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}-structure.xml`.
    """
    options, unknown_params = structure_query_params(params)

    footer_text = []
    if len(unknown_params):
        footer_text.append(f"Ignored unknown query parameters {repr(unknown_params)}")

    resource = params["resource_type"]
    agency_id = params["agency_id"]
    resource_id = params.get("resource_id", "all")
    version = params.get("version", "all")
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
        (resource, agency_id, resource_id, version, item_id, options),
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
    footer_text.extend(
        not_implemented_options(dict(detail="full", references="none"), **options)
    )

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

    try:
        cache.set(cache_key, msg)
    except RuntimeError:
        pass

    add_footer_text(msg, footer_text)

    return msg


def structure_query_params(raw):
    # Prepare a mutable copy of immutable request.args
    params = dict(raw)

    unknown = set(params.keys()) - {"detail", "references"}
    for param in unknown:
        params.pop(param)

    # Set default values and check the two recognized query parameters
    params.setdefault("detail", "full")

    assert params["detail"] in {
        "allstubs",
        "referencestubs",
        "allcompletestubs",
        "referencecompletestubs",
        "referencepartial",
        "full",
    }

    params.setdefault("references", "none")

    assert params["references"] in {
        "none",
        "parents",
        "parentsandsiblings",
        "children",
        "descendants",
        "all",
    }

    return params, unknown


async def handle(request: "starlette.requests.Request"):
    default_ctype = "application/vnd.sdmx.structure+xml;version=2.1"
    ctype = request.headers.get("Accept", default_ctype)
    ctype = {"*/*": default_ctype}.get(ctype, ctype)
    if ctype != default_ctype:
        return Response(status_code=501)

    params = ChainMap(request.path_params, request.query_params)  # type: ignore [arg-type]

    msg = get_structures(request.app.state.config, params)

    finalize_message(msg)

    return Response(sdmx.to_xml(msg, pretty_print=True), media_type=ctype)
