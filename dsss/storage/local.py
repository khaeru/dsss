import sdmx

from dsss import cache


def get(config, path, cache_key):
    # Full path to the blob
    full_path = config["DATA_PATH"] / path

    cache_key = tuple(list(cache_key) + [full_path.stat().st_mtime])

    msg = cache.get(cache_key)
    if msg:
        return msg, None

    with full_path.open("rb") as f:
        msg = sdmx.read_sdmx(f)

    return msg, cache_key


def glob(config, pattern):
    return config["DATA_PATH"].glob("*-structure.xml")
