import pytest


@pytest.fixture(scope="session")
def cached_store_for_app(pytestconfig, specimen):
    from dsss.store import DictStore

    cache_dir = pytestconfig.cache._cachedir.joinpath("sdmx-test-data")
    if not cache_dir.exists():
        pytestconfig.cache.mkdir("sdmx-test-data")

    s = DictStore()
    s.update_from(specimen.base_path)

    yield s


@pytest.fixture(scope="session")
def client(cached_store_for_app):
    from starlette.testclient import TestClient

    from dsss.starlette import build_app

    app = build_app(store=cached_store_for_app)

    yield TestClient(app, base_url="https://example.com")
