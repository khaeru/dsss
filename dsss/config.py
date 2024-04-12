from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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

    def __post_init__(self):
        if not self.cache_dir:
            self.cache_dir = self.data_path.joinpath("cache")
