import pytest

from . import build_app


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
