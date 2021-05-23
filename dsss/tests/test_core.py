import re
from operator import itemgetter

from dsss import build_app

import pytest


@pytest.fixture(scope="session")
def client(tmp_path_factory, specimen):
    # Populate a temporary directory with symlinks to SDMX test data
    test_data_path = tmp_path_factory.mktemp("data")
    for name, target in {
        "ECB_EXR/1/structure-full.xml": "ECB-structure.xml",
        "ECB_EXR/1/M.USD.EUR.SP00.A.xml": "ECB:EXR-data.xml",
    }.items():
        with specimen(name, opened=False) as p:
            test_data_path.joinpath(target).symlink_to(p.resolve())

    # Create the app, backed by the temporary directory
    app = build_app(data_path=test_data_path)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_index(client):
    rv = client.get("/")
    assert (
        b"""This is a <a href="https://github.com/khaeru/dsss">DSSS</a> server."""
        in rv.data
    )


SIMPLE_TESTS = (
    #
    # Structure
    ("/agencyscheme/ECB/all/1.0", 200, b"^<mes:Structure"),
    # Malformed path comes back as a 400 Error message, not 404
    ("/foo/ECB/all/1.0", 400, b"^<mes:Error"),
    # Not implemented
    ("/reportingtaxonomy/ECB", 501, b"^<mes:Error"),
    #
    # Data
    ("/data/ECB,EXR?startPeriod=2011&detail=nodata", 200, b"^<mes:GenericData"),
    (
        "/data/ECB,EXR/M.USD.EUR.SP00.A",
        200,
        b"ignored not implemented path part key=",
    ),
)


@pytest.mark.parametrize(
    "path, code, expr", SIMPLE_TESTS, ids=map(itemgetter(0), SIMPLE_TESTS)
)
def test_path(client, path, code, expr):
    # Request succeeds
    rv = client.get(path)

    # Expected status code
    assert code == rv.status_code

    # Contents match
    assert re.search(expr, rv.data)
