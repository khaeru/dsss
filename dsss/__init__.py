# TODO per the SDMX REST cheat sheet
#
# - Handle HTTP headers:
#   If-Modified-Since Get the data only if something has changed
#   Accept            Select the desired format
#   Accept-Encoding   Compress the response

from pathlib import Path

import sdmx
from flask import Flask, Response, current_app, render_template, request

from .storage import get_data, get_structures
from .util import SDMXResourceConverter, finalize_message

# TODO read via setuptools-scm
__version__ = "0.1"


def build_app() -> Flask:
    """Construct the DSSS :class:`.Flask` application."""
    app = Flask(__name__)

    # Use Jinja2 templates from within the package
    app.template_folder = Path(__file__).parent.joinpath("template")

    # Validate SDMX resource/endpoint names in paths
    app.url_map.converters["sdmx"] = SDMXResourceConverter

    # Don't give 301 when applying default routes
    app.url_map.redirect_defaults = False

    # Add URL rules and versions with defaults
    def add_url_rules(func, parts):
        rule = ""
        for i in range(len(parts)):
            part, _ = parts.pop(0)
            rule += f"/<{part}>"
            app.add_url_rule(rule, defaults=dict(parts), view_func=func)

    add_url_rules(
        structure_view,
        [
            ("sdmx(kind=structure):resource", None),
            ("agency_id", "all"),
            ("resource_id", "all"),
            ("version", "latest"),
            ("item_id", "all"),
        ],
    )

    add_url_rules(
        data_view,
        [
            ("sdmx(kind=data):resource>/<flow_ref", None),
            ("key", "all"),
            ("provider_ref", "all"),
        ],
    )

    app.add_url_rule("/", view_func=index)

    # Path containing data
    # TODO read from a configuration file per
    #      https://flask.palletsprojects.com/en/2.0.x/config/
    app.config["data_path"] = Path.cwd() / "data"

    return app


# Views/endpoints


def data_view(resource, flow_ref, key, provider_ref):
    params = data_query_params(request.args)

    msg = get_data(current_app.config, resource, flow_ref, key, provider_ref, **params)

    finalize_message(
        msg, footer_info=[resource, flow_ref, key, provider_ref, request.args]
    )

    return Response(
        sdmx.to_xml(msg, pretty_print=True),
        content_type="application/vnd.sdmx.genericdata+xml;version=2.1",
    )


def index():
    """Information page."""
    return render_template("index.html")


def structure_view(resource, agency_id, resource_id, version, item_id):
    params = structure_query_params(request.args)

    msg = get_structures(
        current_app.config, resource, agency_id, resource_id, version, item_id, **params
    )

    finalize_message(
        msg,
        footer_info=[resource, agency_id, resource_id, version, item_id, params],
    )

    resp = Response(
        sdmx.to_xml(msg, pretty_print=True),
        content_type="application/vnd.sdmx.structure+xml;version=2.1",
    )

    # Set the 'Server' HTTP header
    # TODO do this somewhere more general, i.e. for all responses
    # TODO also include the defaults, e.g. "Werkzeug/2.0 Python/3.8.6"
    resp.headers["Server"] = f"DSSS/{__version__}"

    return resp


# Utility code


def data_query_params(raw):
    # TODO map the query names to these Pythonic names

    # Prepare a mutable copy of immutable request.args
    params = dict(raw)

    params.setdefault("start_period", None)
    # TODO validate “ISO8601 (e.g. 2014-01) or SDMX reporting period (e.g. 2014-Q3)”
    #      …using pandas
    #
    # Daily/Business YYYY-MM-DD
    # Weekly         YYYY-W[01-53]
    # Monthly        YYYY-MM
    # Quarterly      YYYY-Q[1-4]
    # Semi-annual    YYYY-S[1-2]
    # Annual         YYYY

    params.setdefault("end_period", None)
    # TODO validate (same as above)

    params.setdefault("updated_after", None)
    # TODO validate “Must be percent-encoded (e.g.: 2009-05-15T14%3A15%3A00%2B01%3A00)”

    params.setdefault("first_n_observations", None)
    params.setdefault("last_n_observations", None)
    params.setdefault("dimension_at_observation", "TIME_PERIOD")
    params.setdefault("detail", "full")

    assert params["detail"] in {"full", "dataonly", "serieskeysonly", "nodata"}

    params.setdefault("include_history", False)

    return params


def structure_query_params(raw):
    # Prepare a mutable copy of immutable request.args
    params = dict(raw)

    # Set default values and check the two recognized query parameters
    params.setdefault("detail", "full")

    assert params["detail"] in {
        "allstubs",
        "referencestubs",
        "allcompletestubs",
        "referencecompletestubs",
        "referencepartial",
        "full",
    }

    params.setdefault("references", "none")

    assert params["references"] in {
        "none",
        "parents",
        "parentsandsiblings",
        "children",
        "descendants",
        "all",
    }

    return params


def demo():
    """Run a local demo server."""
    # TODO make click-y, e.g. with --help
    build_app().run(debug=True)
