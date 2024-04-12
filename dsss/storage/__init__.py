from functools import partial
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import dsss.config


def _dispatch(func_name, config: "dsss.config.Config", *args):
    module = import_module(f"dsss.storage.{config.store}")
    return getattr(module, func_name)(config, *args)


get = partial(_dispatch, "get")
glob = partial(_dispatch, "glob")
