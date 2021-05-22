import sdmx


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
    # TODO filter contents
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

    return sdmx.read_sdmx(config["data_path"] / f"{agency_id}-structure.xml")
