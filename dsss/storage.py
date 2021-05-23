import sdmx
from flask import abort

from . import cache
from .util import add_footer_text, not_implemented_options, not_implemented_path


def get_data(config, resource, agency_id, flow_id, version, key, provider_ref, params):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}:{flow_id}-structure.xml`
    """
    options, unknown_params = data_query_params(params)

    footer_text = []
    if len(unknown_params):
        footer_text.append(f"Ignored unknown query parameters {repr(unknown_params)}")

    # ‘Repository’ of *all* data for this flow
    repo_path = config["data_path"] / f"{agency_id}:{flow_id}-{resource}.xml"

    cache_key = (
        repo_path.stat().st_mtime,
        resource,
        agency_id,
        flow_id,
        version,
        key,
        provider_ref,
        options,
    )
    msg = cache.get(cache_key)
    if msg:
        add_footer_text(msg, footer_text)
        return msg

    # Cache miss
    repo = sdmx.read_sdmx(repo_path)

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
            **options,
        )
    )

    cache.set(cache_key, msg)

    add_footer_text(repo, footer_text)

    return repo


def data_query_params(raw):
    # Prepare a mutable copy of immutable request.args
    params = dict(raw)

    unknown = set(params.keys()) - {
        "startPeriod",
        "endPeriod",
        "updatedAfter",
        "firstNObservations",
        "lastNObservations",
        "dimensionAtObservation",
        "detail",
        "includeHistory",
    }

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

    return params, unknown


def get_structures(config, resource, agency_id, resource_id, version, item_id, params):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}-structure.xml`.
    """
    options, unknown_params = structure_query_params(params)

    footer_text = []
    if len(unknown_params):
        footer_text.append(f"Ignored unknown query parameters {repr(unknown_params)}")

    if agency_id == "all":
        # Determine the list of all providers being served
        agency_ids = list(
            map(
                lambda p: p.name.split("-")[0],
                config["data_path"].glob("*-structure.xml"),
            )
        )

        if len(agency_ids) > 1:
            raise NotImplementedError("Combine structures from ≥2 providers")

        # Use the first provider
        agency_id = agency_ids[0]

    # ‘Repository’ of *all* structures
    repo_path = config["data_path"] / f"{agency_id}-structure.xml"

    cache_key = (
        repo_path.stat().st_mtime,
        resource,
        agency_id,
        resource_id,
        version,
        item_id,
        options,
    )

    msg = cache.get(cache_key)
    if msg:
        add_footer_text(msg, footer_text)
        return msg

    # Cache miss

    repo = sdmx.read_sdmx(repo_path)

    # Filtered message
    msg = sdmx.message.StructureMessage()

    # sdmx.model class for the resource
    cls = sdmx.model.get_class(resource)

    if cls is None:
        footer_text.append(f"resource={repr(resource)}")
        abort(501, *footer_text)

    # Source and target collections
    collection = repo.objects(cls)
    target = msg.objects(cls)

    if collection is None:
        abort(501, *footer_text)

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
            abort(404, *footer_text)

    cache.set(cache_key, msg)

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
