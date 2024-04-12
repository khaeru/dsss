import logging
from typing import TYPE_CHECKING

import sdmx

from dsss import cache

if TYPE_CHECKING:
    import dsss.config

log = logging.getLogger(__name__)


def get(config: "dsss.config.Config", path, cache_key):
    # Full path to the blob
    full_path = config.data_path.joinpath(path)

    cache_key = tuple(list(cache_key) + [full_path.stat().st_mtime])

    try:
        msg = cache.get(cache_key)
        if msg:
            return msg, None
    except RuntimeError:
        pass

    log.info(f"Read from {full_path}")

    with full_path.open("rb") as f:
        msg = sdmx.read_sdmx(f)

    log.info(f"Obtained:\n{repr(msg)}")

    return msg, cache_key


def glob(config, pattern):
    return config["DATA_PATH"].glob("*-structure.xml")
