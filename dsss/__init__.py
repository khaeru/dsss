from importlib.metadata import PackageNotFoundError, version

from .starlette import build_app

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "999"


__all__ = ["build_app"]
