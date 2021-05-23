from dsss import build_app

import pytest


@pytest.fixture
def client(tmp_path_factory):
    app = build_app(data_path=tmp_path_factory.mktemp("data"))
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_index(client):
    rv = client.get("/")
    assert (
        b"""This is a <a href="https://github.com/khaeru/dsss">DSSS</a> server."""
        in rv.data
    )
