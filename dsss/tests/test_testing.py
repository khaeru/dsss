import pytest


@pytest.mark.parametrize(
    "agency_id, count",
    (
        ("BIS", 20),
        ("ECB", 22),  # Could be 22
        ("ESTAT", 27),  # Could be 34
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
    assert count <= len(cached_store_for_app.list(maintainer=agency_id))
