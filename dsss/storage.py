import sdmx

#: Prepared SDMX ErrorMessage objects.
ERRORS = {
    404: sdmx.message.ErrorMessage(footer=sdmx.message.Footer(code=404)),
    501: sdmx.message.ErrorMessage(footer=sdmx.message.Footer(code=501)),
}


def get_data(config, resource, flow_ref, key, provider_ref, **options):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{flow_ref}-structure.xml`
    """
    # TODO filter contents
    # TODO cache pickled objects
    return sdmx.read_sdmx(config["data_path"] / f"{flow_ref}-{resource}.xml")


def get_structures(
    config, resource, agency_id, resource_id, version, item_id, **options
):
    """Return an SDMX DataMessage with the requested contents.

    The current version loads a file from the data path named
    :file:`{agency_id}-structure.xml`.
    """
    # TODO cache pickled objects

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
    repo = sdmx.read_sdmx(config["data_path"] / f"{agency_id}-structure.xml")

    # Filtered message
    msg = sdmx.message.StructureMessage()

    # sdmx.model class for the resource
    cls = sdmx.model.get_class(resource)

    # Source and target collections
    collection = repo.objects(cls)
    target = msg.objects(cls)

    if collection is None:
        return ERRORS[501]

    if resource_id == "all":
        # Copy all object
        target.update(collection)
    else:
        try:
            # Copy a single object
            getattr(msg, resource)[resource_id] = collection[resource_id]
        except KeyError:
            # Not found
            return ERRORS[404]

    return msg
