import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Optional


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

    # Configure caching
    cache_type: str = "FileSystemCache"

    cache_dir: Optional[Path] = None

    version_string: str = field(default_factory=_version_string)

    def __post_init__(self):
        if not self.cache_dir:
            self.cache_dir = self.data_path.joinpath("cache")
