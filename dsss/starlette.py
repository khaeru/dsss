"""Starlette implementation of the SDMX REST API.


.. todo:: per the SDMX REST cheat sheet:

  - Handle HTTP headers:

    - ``If-Modified-Since`` Get the data only if something has changed.
    - ``Accept-Encoding`` Compress the response.
"""

from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import HTMLResponse
from starlette.routing import Route

from .common import SDMXResponse, gen_error_message
from .config import Config

if TYPE_CHECKING:
    import starlette.requests


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware that sets the ``Server`` and ``Prepared`` HTTP headers."""

    def __init__(self, app, *, server: str):
        super().__init__(app)
        self.server_header = server

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        response.headers["Server"] = self.server_header
        # TODO Check if necessary, or if starlette does this automatically
        response.headers["Prepared"] = datetime.now().isoformat()

        return response


def build_app(**config_kwargs):
    """Construct and return a :class:`.Starlette` DSSS app."""
    # Parse configuration from arguments
    config = Config(**config_kwargs)

    # Collection of routes
    routes = [Route("/", index)]

    # Collect routes from each endpoint module
    for endpoint in (
        "availability",
        "data",
        "metadata",
        "registration",
        "schema",
        "structure",
    ):
        mod = import_module(f"dsss.{endpoint}")
        routes.extend(mod.get_routes())

    # Create app
    app = Starlette(
        debug=config.debug,
        routes=routes,
        # Anything else is user error in constructing a valid URL
        exception_handlers={
            # 400: handle_exception,
            404: handle_exception,
            # 501: handle_exception,
        },
        middleware=[
            Middleware(CustomHeaderMiddleware, server=config.version_string),
            Middleware(GZipMiddleware, minimum_size=1000),
        ],
    )

    # Store configuration on the app instance
    app.state.config = config

    return app


async def handle_exception(request: "starlette.requests.Request", exc):
    """Handle errors."""
    code = exc.status_code
    text = repr(exc)

    if code == 404:
        # 404 indicates a routing failure, e.g. the user gave a malformed URL
        # The SDMX REST standard specifies this is a "400 Syntax error"
        text = f"{request.url} is not a valid SDMX REST path"
        code = 400

    return SDMXResponse(gen_error_message(code, text), status_code=code)


async def index(request: "starlette.requests.Request"):
    """Return a bare-bones HTML info page on from the base URL."""
    return HTMLResponse(
        """<p>This is a <a href="https://github.com/khaeru/dsss">DSSS</a> server.</p>"""
    )
