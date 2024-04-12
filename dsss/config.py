import logging
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Literal


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
    # TODO Read from file
    debug: bool = True

    #: Storage module to use.
    store: Literal["google_cloud_storage", "local"] = "local"

    #: Path containing data.
    data_path: Path = field(default_factory=lambda: Path.cwd().joinpath("data"))

    version_string: str = field(default_factory=_version_string)

    def __post_init__(self):
        log = logging.getLogger("dsss")
        log.setLevel(logging.DEBUG if self.debug else logging.INFO)
