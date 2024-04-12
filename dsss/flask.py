# TODO per the SDMX REST cheat sheet
#
# - Handle HTTP headers:
#   If-Modified-Since Get the data only if something has changed
#   Accept-Encoding   Compress the response

import logging
import os
from pathlib import Path

import flask


def build_app(store=None, data_path=None, **kwargs) -> flask.Flask:
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

    # Don't give 301 when applying default routes
    app.url_map.redirect_defaults = False

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

    return app


#  Utility code


def demo():
    """Run a local demo server."""
    # TODO make click-y, e.g. with --help
    build_app().run(debug=True)


def serve():
    """Run a non-debug server."""
    build_app().run()
