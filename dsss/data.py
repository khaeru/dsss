from . import cache, storage
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
    repo, cache_key = storage.get(
        config,
        f"{agency_id}:{flow_id}-{resource}.xml",
        (
            resource,
            agency_id,
            flow_id,
            version,
            key,
            provider_ref,
            options,
        ),
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
            **options,
        )
    )

    cache.set(cache_key, repo)

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
