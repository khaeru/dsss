import re
from io import BytesIO
from operator import itemgetter

import pytest
import sdmx
import sdmx.rest.v21
import sdmx.rest.v30
import sdmx.tests.test_rest
from sdmx.model import common
from sdmx.rest.common import Resource


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
    # No return values
    ("/reportingtaxonomy/ECB", 200, b"<mes:Error"),
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
    match = re.search(expr, rv.content)
    if not match:
        print(rv.content.decode())
        assert False

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


def test_get_data(cached_store_for_app):
    from dsss.config import Config
    from dsss.data import get_data

    config = Config(store=cached_store_for_app)

    result = get_data(
        config,
        path_params=dict(
            flow_ref=["ECB", "EXR", "latest"], key="all", provider_ref="all"
        ),
        query_params=dict(),
    )

    assert 1 == len(result.data)
    ds = result.data[0]
    assert 252 == len(ds)


def test_data(client, source):
    url = "/data/ECB,EXR"
    # Query succeeds
    rv = client.get(url)
    assert 200 == rv.status_code

    # Response can be parsed as SDMX-ML
    msg = sdmx.read_sdmx(BytesIO(rv.content))

    # Collection has the expected number of entries
    assert 1 == len(msg.data)


@pytest.mark.parametrize("url_class", [sdmx.rest.v21.URL, sdmx.rest.v30.URL])
@pytest.mark.parametrize(
    "resource_type, count",
    (
        # ("actualconstraint", 0),
        ("agencyscheme", 3),
        # ("allowedconstraint", 0),
        # ("attachementconstraint", 0),
        # ("availableconstraint", 0),
        ("categorisation", 7),
        ("categoryscheme", 3),
        ("codelist", 88),
        ("conceptscheme", 19),
        # ("contentconstraint", 0),
        # ("customtypescheme", 0),
        # ("data", 0),
        # ("dataconsumerscheme", 0),
        ("dataflow", 677),
        # ("dataproviderscheme", 0),
        ("datastructure", 22),
        # ("hierarchicalcodelist", 0),
        # ("metadata", 0),
        # ("metadataflow", 0),
        # ("metadatastructure", 0),
        # ("namepersonalisationscheme", 0),
        # ("organisationscheme", 0),
        # ("organisationunitscheme", 0),
        # ("process", 0),
        # ("provisionagreement", 0),
        # ("reportingtaxonomy", 0),
        # ("rulesetscheme", 0),
        # ("schema", 0),
        # ("structure", 0),
        # ("structureset", 0),
        # ("transformationscheme", 0),
        # ("userdefinedoperatorscheme", 0),
        # ("vtlmappingscheme", 0),
    ),
)
def test_structure_all(client, source, url_class, resource_type, count) -> None:
    from sdmx.model.v21 import get_class

    # Identify the resource and artefact class
    resource = Resource[resource_type]
    klass = get_class(resource)

    # Construct the URL
    url = url_class(source, resource, agency_id="ALL").join()

    # Query succeeds
    rv = client.get(url)
    assert 200 == rv.status_code

    # Response can be parsed as SDMX-ML
    msg = sdmx.read_sdmx(BytesIO(rv.content))

    # Collection has the expected number of entries
    assert count == len(msg.objects(klass))


@pytest.mark.parametrize(
    "url, count",
    (
        ("/codelist/ALL/all/latest", 88),
        ("/codelist/FR1/all/latest", 7),
        ("/codelist/ALL/CL_UNIT_MULT/latest", 5),
    ),
)
def test_structure(client, source, url, count):
    # Query succeeds
    rv = client.get(url)
    assert 200 == rv.status_code

    # Response can be parsed as SDMX-ML
    msg = sdmx.read_sdmx(BytesIO(rv.content))

    # Collection has the expected number of entries
    assert count == len(msg.objects(common.Codelist))
