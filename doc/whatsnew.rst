What's new?
***********

.. Next release
.. ============

v1.1.0 (2024-09-04)
===================

- Generate stable, unique :mod:`.store` keys for :class:`sdmx.model.v21.MetadataSet` (:pull:`10`).
- Improve :mod:`.store`; add the :class:`.GitStore` and :class:`.UnionStore` classes (:pull:`9`).
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
