from functools import partial
from importlib import import_module


def _dispatch(func_name, config, *args):
    module = import_module(f"dsss.storage.{config['DSSS_STORE']}")
    return getattr(module, func_name)(config, *args)


get = partial(_dispatch, "get")
glob = partial(_dispatch, "glob")
