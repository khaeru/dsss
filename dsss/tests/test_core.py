import re
from io import BytesIO
from operator import itemgetter

import pytest
import sdmx
import sdmx.rest.v21
import sdmx.rest.v30
import sdmx.tests.test_rest


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
def test_path0(client, path, code, expr):
    # Request succeeds
    rv = client.get(path)

    # Expected status code
    assert code == rv.status_code

    # Contents match
    assert re.search(expr, rv.content)

    # Response can be parsed using sdmx1
    sdmx.read_sdmx(BytesIO(rv.content))


@pytest.fixture
def source():
    from sdmx.source import Source

    yield Source(id="A0", url="https://example.com", name="Test source")


@pytest.mark.parametrize(
    "url_class, expected_index", ((sdmx.rest.v21.URL, 0), (sdmx.rest.v30.URL, 1))
)
@pytest.mark.parametrize(
    "resource_type, kw, expected0, expected1", sdmx.tests.test_rest.PARAMS
)
def test_path1(
    client, source, url_class, expected_index, resource_type, kw, expected0, expected1
) -> None:
    if [expected0, expected1][expected_index] is None:
        return  # Not a constructable URL

    # Create the URL, extract the path
    url = url_class(source, resource_type, resource_id="ID0", **kw).join()
    # print(url)

    rv = client.get(url)
    # print(rv.content.decode())

    # Expected status code
    assert 400 != rv.status_code
