import pytest
from sdmx.model import v21


@pytest.mark.parametrize(
    "agency_id, count",
    (
        ("BIS", 20),
        ("ECB", 22),  # Could be 22
        ("ESTAT", 26),  # Could be 34
        ("FR1", 676),  # Could be 1344
        ("IAEG-SDGs", 1),
        ("IAEG", 1),
        ("IMF_STA", 4),  # Could be 37
        ("IMF", 19),  # Could be 43
        ("ISO", 1),
        ("IT1", 21),
        ("NONE", 0),  # Could be 29
        ("OECD.DAF", 1),
        ("OECD", 1),
        ("SDMX", 37),
        ("SPC", 2),
        ("STC", 0),
        ("TEST", 1),
        ("UNICEF.EMOPS", 2),
        ("UNICEF", 23),
        ("UNSD", 3),  # Could be 4
    ),
)
def test_cached_store_for_app0(cached_store_for_app, agency_id, count) -> None:
    # NB Use <= to allow for additions to specimens; == to identify/update values
    s = cached_store_for_app
    assert count <= len(s.list(maintainer=agency_id))


def test_cached_store_for_app1(cached_store_for_app):
    """Ensure the cached_store_for_app test fixture contains the necessary artefacts."""
    s = cached_store_for_app

    result = s.list(klass=v21.DataflowDefinition, maintainer="ECB", id="EXR")
    assert len(result)
