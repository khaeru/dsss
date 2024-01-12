# TODO per the SDMX REST cheat sheet
#
# - Handle HTTP headers:
#   If-Modified-Since Get the data only if something has changed
#   Accept-Encoding   Compress the response

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import flask
import flask_caching
import sdmx
import werkzeug
from flask import Response, abort, current_app, render_template, request

from .data import get_data
from .structure import get_structures
from .util import (
    FlowRefConverter,
    SDMXResourceConverter,
    finalize_message,
    gen_error_message,
)

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "999"


def build_app(
    store=None, data_path=None, cache_type=None, cache_dir=None, **kwargs
) -> flask.Flask:
    """Construct the DSSS :class:`.Flask` application."""
    app = flask.Flask(__name__)

    # Pass other keyword arguments as Flask configuration
    app.config.from_mapping(kwargs)

    # Increase logging verbosity
    level = logging.DEBUG if app.config["DEBUG"] else logging.INFO
    logging.getLogger("root").setLevel(level)
    app.logger.setLevel(level)

    try:
        # Read configuration from a file specified by an environment variable
        config_path = Path(os.environ["DSSS_CONFIG"])
    except KeyError:
        app.logger.info("No environment variable DSSS_CONFIG")
    else:
        if not config_path.is_absolute():
            # Convert a relative to an absolute path
            config_path = Path.cwd().joinpath(config_path).resolve()
        app.logger.info(f"Read configuration from {config_path}")
        app.config.from_pyfile(str(config_path))

    # Built-in Flask settings

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

    # Error handlers
    for status_code in (400, 404, 501):
        app.register_error_handler(status_code, handle_error)

    # Configuration
    app.config.setdefault("DSSS_STORE", store or "local")

    def use_path_defaults(name, arg, default):
        # Set the default if not loaded from a config file (above)
        app.config.setdefault(name, default)

        if arg:
            # Override with a direct function argument
            app.config[name] = arg

        # Make an absolute path
        app.config[name] = Path(app.config[name]).resolve()

        app.logger.info(f"Configured {name}={app.config[name]}")

    # Path containing data
    use_path_defaults("DATA_PATH", data_path, Path.cwd() / "data")

    # Configure caching
    app.config.setdefault("CACHE_TYPE", "FileSystemCache")

    use_path_defaults("CACHE_DIR", cache_dir, app.config["DATA_PATH"].joinpath("cache"))

    flask_caching.Cache(app)

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


def handle_error(e):
    """Handle errors."""
    code = e.code
    text = e.description

    if code == 404:
        # 404 indicates a routing failure, e.g. the user gave a malformed URL
        # The SDMX REST standard specifies this is a "400 Syntax error"
        text = f"{request.path} is not a valid SDMX REST path"
        code = 400

    return gen_error_message(code, text), code


def demo():
    """Run a local demo server."""
    # TODO make click-y, e.g. with --help
    build_app().run(debug=True)


def serve():
    """Run a non-debug server."""
    build_app().run()
