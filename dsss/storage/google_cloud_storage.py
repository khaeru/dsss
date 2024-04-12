import logging

import sdmx
from google.cloud import storage

log = logging.getLogger(__name__)

client = storage.Client()


def get(config, path, cache_key):
    # Full path to the blob
    full_path = config["DATA_PATH"] / path

    # Split the bucket name from the blob name
    bucket_name = full_path.parts[0]
    blob_name = full_path.relative_to(bucket_name)

    bucket = client.get_bucket(bucket_name)
    blob = bucket.get_blob(blob_name)

    cache_key = tuple(list(cache_key) + [blob.time_created])

    # msg = cache.get(cache_key)
    msg = None
    if msg:
        return msg, None

    log.info(f"Read from {full_path}")

    with blob.open("rb") as f:
        msg = sdmx.read_sdmx(f)

    log.info(f"Obtained:\n{repr(msg)}")

    return msg, cache_key


def glob(config, pattern):
    raise NotImplementedError
