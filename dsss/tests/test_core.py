import re
from io import BytesIO
from operator import itemgetter

import pytest
import sdmx


def test_index(client):
    rv = client.get("/")
    assert (
        b"""This is a <a href="https://github.com/khaeru/dsss">DSSS</a> server."""
        in rv.content
    )


SIMPLE_TESTS = (
    #
    # Structure
    # SDMX-REST 1.5.0 / SDMX 2.1
    ("/agencyscheme/ECB/all/1.0", 200, b"<mes:Structure"),
    # SDMX-REST 2.1.0 / SDMX 3.0
    ("/structure/agencyscheme/ECB/all/1.0", 200, b"<mes:Structure"),
    # Malformed path comes back as a 400 Error message, not 404
    ("/foo/ECB/all/1.0", 400, b"<mes:Error"),
    # Not implemented
    ("/reportingtaxonomy/ECB", 501, b"<mes:Error"),
    #
    # Data
    ("/data/ECB,EXR?startPeriod=2011&detail=nodata", 200, b"<mes:GenericData"),
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
    assert re.search(expr, rv.content)

    # Response can be parsed using sdmx1
    sdmx.read_sdmx(BytesIO(rv.content))
