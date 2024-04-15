import logging
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import dsss.store


def _version_string() -> str:
    return " ".join(
        [
            f"DSSS/{version('dsss')}",
            f"Starlette/{version('starlette')}",
            f"Python/{sys.version.split()[0]}",
        ]
    )


@dataclass
class Config:
    #: Storage module to use.
    store: "dsss.store.Store"

    # TODO Read from file
    debug: bool = True

    #: Path containing data.
    data_path: Path = field(default_factory=lambda: Path.cwd().joinpath("data"))

    version_string: str = field(default_factory=_version_string)

    def __post_init__(self):
        log = logging.getLogger("dsss")
        log.setLevel(logging.DEBUG if self.debug else logging.INFO)
