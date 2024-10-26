What's new?
***********

.. Next release
.. ============

v1.3.0 (2024-10-26)
===================

- :class:`.FileStore` and related classes are usable on Windows file systems (:pull:`17`); directory and file paths are constructed without using invalid characters such as ``:``.
   This does *not* imply that :mod:`dsss` is fully supported on Windows.

v1.2.0 (2024-10-25)
===================

- Python 3.13 (`released 2024-10-07 <https://www.python.org/downloads/release/python-3130/>`_) is fully supported (:pull:`13`).
- Python 3.9 and 3.10 are fully supported (:pull:`15`).
- Bug fix: :meth:`.Store.assign_version` would increment the 1-th, instead of largest, existing version (:pull:`14`).
- Bug fix: :class:`.FileStore` raised :class:`FileNotFoundError` or :class:`IsADirectoryError`, instead of :class:`KeyError`, on a missing key (:pull:`14`).

v1.1.0 (2024-09-04)
===================

- Generate stable, unique :mod:`.store` keys for :class:`sdmx.model.v21.MetadataSet` (:pull:`10`).
- Improve :mod:`.store`; add the :class:`.GitStore` and :class:`.UnionStore` classes (:pull:`9`, :pull:`12`).
- Expand documentation of :class:`.Store` (:pull:`8`).

v1.0.0 (2024-07-10)
===================

In this initial release, :mod:`dsss` *tolerates* all the queries possible using the `SDMX REST cheat sheet <https://github.com/sdmx-twg/sdmx-rest/blob/master/doc/rest_cheat_sheet.pdf>`_.
‘Tolerate’ means that DSSS will respond to every possible query with an SDMX-ML message, although possibly an SDMX-ML ErrorMessage with code 501 indicating the given feature(s) are not implemented.

Thus the code:

- Respects optional path parts.
- Returns appropriate error messages for unavailable resources.
- Filters structures (partial implementation).
- Filters data (partial implementation).
- Returns footer or other messages when the response is not fully filtered per path and query parameters.
- Provides :doc:`documentation local deployment <usage>`.
- Includes an initial test suite.
- Supports, and is tested on, Ubuntu Linux and Python ≥ 3.11.
