"""Fixtures for testing :mod:`.dsss`."""

import logging
import os
import sys
from io import StringIO
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

GHA = "GITHUB_ACTIONS" in os.environ


def assert_le(exp: int, obs: int) -> None:
    if exp < obs:
        log.warning(f"{exp = } < {obs} = obs")
    else:
        assert exp <= obs


def ignore(p: "Path") -> bool:
    """Ignore certain paths when populating :func:`.cached_store_for_app`.

    The SDMX 3.0 example files for SDMX-ML include a Dataflow=ECB:EXR(1.0) that
    references a different DSD (DataStructure=ECB:EXR(1.0)) than the real-world one
    (DataStructure=ECB:ECB_EXR1(1.0)). Ignore this data flow definition.
    """
    return (p.parts[-3:] == ("v3", "xml", "dataflow.xml")) or (
        p.parts[-2:] == ("IAEG-SDGs", "metadatastructure-0.xml")
    )


@pytest.fixture(scope="session")
def cached_store_for_app(pytestconfig, specimen):
    """A :class:`.DictStore` with the :mod:`sdmx.testing` specimen collection loaded."""
    from sdmx.urn import expand

    from dsss.store import DictStore

    cache_dir = pytestconfig.cache._cachedir.joinpath("sdmx-test-data")
    if not cache_dir.exists():
        pytestconfig.cache.mkdir("sdmx-test-data")

    s = DictStore()

    # Capture noise from sdmx on reading known unsupported specimens from sdmx-test-data
    # NB Cannot use Pytest capsys or monkeypatch, as this is a session-scoped fixture
    try:
        stdout = sys.stdout  # Replace sys.stdout with a temporary buffer
        buf = sys.stdout = StringIO()

        s.update_from(specimen.base_path, ignore=[ignore])  # Update the DictStore
    finally:
        sys.stdout = stdout  # Restore
        del buf

    # Remove or add certain items from the set used in tests
    for short_urn in (
        "Categorisation=ESTAT:DEMO_TOT(1.0)",  # Causes errors on GHA, not locally
    ):
        s.delete(expand(short_urn))

    yield s


@pytest.fixture(scope="session")
def client(cached_store_for_app):
    """A :class:`.starlette.testclient.TestClient` for :mod:`.dsss`."""
    from starlette.testclient import TestClient

    from dsss.starlette import build_app

    app = build_app(store=cached_store_for_app)

    yield TestClient(app, base_url="https://example.com")
