# TODO per the SDMX REST cheat sheet
#
# - Handle HTTP headers:
#   If-Modified-Since Get the data only if something has changed
#   Accept-Encoding   Compress the response

import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

import flask
import flask_caching
import sdmx
import werkzeug
from flask import Response, abort, current_app, render_template, request

from .storage import get_data, get_structures
from .util import FlowRefConverter, SDMXResourceConverter, finalize_message


try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "UNKNOWN"


def build_app() -> flask.Flask:
    """Construct the DSSS :class:`.Flask` application."""
    app = flask.Flask(__name__)

    # Use Jinja2 templates from within the package
    app.template_folder = Path(__file__).parent.joinpath("template")

    # Validate SDMX resource/endpoint names in paths
    app.url_map.converters["sdmx"] = SDMXResourceConverter
    app.url_map.converters["flow_ref"] = FlowRefConverter

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
            ("sdmx(kind=data):resource>/<flow_ref:flow_ref", None),
            ("key", "all"),
            ("provider_ref", "all"),
        ],
    )

    app.add_url_rule("/", view_func=index)

    app.after_request(add_server)

    # Path containing data
    # TODO read from a configuration file per
    #      https://flask.palletsprojects.com/en/2.0.x/config/
    app.config["data_path"] = Path.cwd() / "data"

    # Configure caching
    flask_caching.Cache(
        app,
        config=dict(
            CACHE_TYPE="FileSystemCache",
            CACHE_DIR=app.config["data_path"].joinpath("cache"),
        ),
    )

    return app


# Views/endpoints


def data_view(resource, flow_ref, key, provider_ref):
    default_ctype = "application/vnd.sdmx.genericdata+xml;version=2.1"
    ctype = request.headers.get("Accept", default_ctype)
    ctype = {"*/*": default_ctype}.get(ctype, ctype)
    if ctype != "application/vnd.sdmx.genericdata+xml;version=2.1":
        abort(501)

    # Unpack flow_ref into agency_id, flow_id, version
    msg = get_data(
        current_app.config, resource, *flow_ref, key, provider_ref, request.args
    )

    finalize_message(msg)

    return Response(sdmx.to_xml(msg, pretty_print=True), content_type=ctype)


def index():
    """Information page."""
    return render_template("index.html")


def structure_view(resource, agency_id, resource_id, version, item_id):
    default_ctype = "application/vnd.sdmx.structure+xml;version=2.1"
    ctype = request.headers.get("Accept", default_ctype)
    ctype = {"*/*": default_ctype}.get(ctype, ctype)
    if ctype != "application/vnd.sdmx.structure+xml;version=2.1":
        abort(501)

    msg = get_structures(
        current_app.config,
        resource,
        agency_id,
        resource_id,
        version,
        item_id,
        request.args,
    )

    finalize_message(msg)

    return Response(sdmx.to_xml(msg, pretty_print=True), content_type=ctype)


# Utility code


def add_server(response):
    """Set the 'Server' HTTP header."""
    response.headers["Server"] = " ".join(
        [
            f"DSSS/{__version__}",
            f"Flask/{flask.__version__}",
            # The following reproduce the Flask defaults
            f"Werkzeug/{werkzeug.__version__}",
            f"Python/{sys.version.split()[0]}",
        ]
    )
    return response


def demo():
    """Run a local demo server."""
    # TODO make click-y, e.g. with --help
    build_app().run(debug=True)
