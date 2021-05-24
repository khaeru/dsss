import sdmx
from flask import abort

from . import cache, storage
from .util import add_footer_text, not_implemented_options, not_implemented_path


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
