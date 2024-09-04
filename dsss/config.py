"""Configuration for :mod:`.dsss`."""

import logging
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import dsss.store


def version_string() -> str:
    """Return a string with versions of :mod:`.dsss`, :mod:`.starlette`, and Python."""
    return " ".join(
        [
            f"DSSS/{version('dsss')}",
            f"Starlette/{version('starlette')}",
            f"Python/{sys.version.split()[0]}",
        ]
    )


@dataclass
class Config:
    """Configuration for a server instance."""

    #: Storage class to use; the fully qualified name of a class in :mod:`.store`.
    store: "dsss.store.Store"

    #: Start the server in debugging mode.
    #:
    #: .. todo:: Read this setting from file.
    debug: bool = True

    #: Path containing data.
    data_path: Path = field(default_factory=lambda: Path.cwd().joinpath("data"))

    version_string: str = field(default_factory=version_string)

    def __post_init__(self):
        log = logging.getLogger("dsss")
        log.setLevel(logging.DEBUG if self.debug else logging.INFO)
