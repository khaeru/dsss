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
    return sdmx.read_sdmx(config["data_path"] / f"{agency_id}-structure.xml")
