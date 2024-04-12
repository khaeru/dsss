import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path


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
    debug: bool = True

    #: Storage module to use.
    store: str = "local"

    #: Path containing data.
    data_path: Path = field(default_factory=lambda: Path.cwd().joinpath("data"))

    version_string: str = field(default_factory=_version_string)
