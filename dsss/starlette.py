from importlib import import_module
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from .common import SDMXResponse, gen_error_message
from .config import Config

if TYPE_CHECKING:
    import starlette.requests


def build_app(**config_kwargs):
    # Parse configuration from arguments
    config = Config(**config_kwargs)

    routes = [Route("/", index)]
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

    app = Starlette(
        debug=config.debug,
        routes=routes,
        # Anything else is user error in constructing a valid URL
        exception_handlers={
            # 400: handle_exception,
            404: handle_exception,
            # 501: handle_exception,
        },
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
    return HTMLResponse(
        """<p>This is a <a href="https://github.com/khaeru/dsss">DSSS</a> server.</p>"""
    )
