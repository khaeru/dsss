from typing import TYPE_CHECKING, List, Mapping

import sdmx
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


def get_routes():
    return [
        Route("/data/{flow_ref}", handle),
        Route("/data/{flow_ref}/{key}", handle),
        Route("/data/{flow_ref}/{key}/{provider_ref}", handle),
    ]


def handle_query_params(url_class, expr: str, values: Mapping) -> dict:
    """Extend :attr:`.query` with parts from `expr`, a " "-delimited string."""
    result = {}
    for p in map(url_class._all_parameters.__getitem__, expr.split()):
        result[p.name] = values.get(p.camelName, p.default)

    return result


async def handle(request: "starlette.requests.Request"):
    default_ctype = "application/vnd.sdmx.genericdata+xml;version=2.1"
    ctype = request.headers.get("Accept", default_ctype)
    ctype = {"*/*": default_ctype}.get(ctype, ctype)
    if ctype != default_ctype:
        return Response(status_code=501)

    qp = handle_query_params(
        sdmx.rest.v21.URL,
        "start_period end_period updated_after first_n_observations "
        "last_n_observations dimension_at_observation detail_d include_history",
        request.query_params,
    )

    msg = get_data(request.app.state.config, request.path_params, qp)

    finalize_message(msg)

    return Response(sdmx.to_xml(msg, pretty_print=True), media_type=ctype)


def get_data(config: "dsss.config.Config", path_params: Mapping, query_params: Mapping):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}:{flow_id}-structure.xml`
    """
    footer_text: List[str] = []

    agency_id, flow_id = path_params["flow_ref"].split(",")
    resource = "data"
    version = path_params.get("version", "all")
    provider_ref = path_params.get("provider_ref", None)
    key = path_params.get("key", None)

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
    footer_text.extend(
        not_implemented_options(
            dict(
                start_period=None,
                end_period=None,
                updated_after=None,
                first_n_observations=None,
                last_n_observations=None,
                detail="full",
                dimension_at_observation="TIME_PERIOD",
                include_history=False,
            ),
            **query_params,
        )
    )

    try:
        cache.set(cache_key, repo)
    except RuntimeError:
        pass

    add_footer_text(repo, footer_text)

    return repo


def data_query_params(raw):
    # Prepare a mutable copy of immutable request.args
    params = dict(raw)

    params["start_period"] = params.pop("startPeriod", None)
    # TODO validate “ISO8601 (e.g. 2014-01) or SDMX reporting period (e.g. 2014-Q3)”
    #      …using pandas
    #
    # Daily/Business YYYY-MM-DD
    # Weekly         YYYY-W[01-53]
    # Monthly        YYYY-MM
    # Quarterly      YYYY-Q[1-4]
    # Semi-annual    YYYY-S[1-2]
    # Annual         YYYY

    params["end_period"] = params.pop("endPeriod", None)
    # TODO validate (same as above)

    params["updated_after"] = params.pop("updatedAfter", None)
    # TODO validate “Must be percent-encoded (e.g.: 2009-05-15T14%3A15%3A00%2B01%3A00)”

    params["first_n_observations"] = params.pop("firstNObservations", None)
    params["last_n_observations"] = params.pop("lastNObservations", None)
    params["dimension_at_observation"] = params.pop(
        "dimensionAtObservation", "TIME_PERIOD"
    )

    params.setdefault("detail", "full")
    assert params["detail"] in {"full", "dataonly", "serieskeysonly", "nodata"}

    # TODO convert strings like "false", "False", "0"
    params["include_history"] = params.pop("includeHistory", False)

    return params, set()
