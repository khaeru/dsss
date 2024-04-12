import pytest


@pytest.fixture(scope="session")
def tmp_data_for_app(tmp_path_factory, specimen):
    # Populate a temporary directory with symlinks to SDMX test data
    test_data_path = tmp_path_factory.mktemp("data")
    for name, target in {
        "ECB_EXR/1/structure-full.xml": "ECB-structure.xml",
        "ECB_EXR/1/M.USD.EUR.SP00.A.xml": "ECB:EXR-data.xml",
    }.items():
        with specimen(name, opened=False) as p:
            test_data_path.joinpath(target).symlink_to(p.resolve())

    yield test_data_path


@pytest.fixture(
    scope="session",
    params=[
        "flask",
        "starlette",
    ],
)
def client(request, tmp_data_for_app):
    config = dict(data_path=tmp_data_for_app)

    if request.param == "flask":
        from dsss.flask import build_app

        # Create the app, backed by the temporary directory
        config.update(TESTING=True)
        app = build_app(**config)

        with app.test_client() as client:
            yield client
    elif request.param == "starlette":
        from starlette.testclient import TestClient

        from dsss.starlette import build_app

        app = build_app(**config)

        yield TestClient(app)
