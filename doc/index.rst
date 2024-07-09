DSSS: a dead-simple SDMX server
*******************************

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage
   api
   whatsnew

Roadmap
=======

For a 1.0 release, the code will *tolerate* all the queries possible using the `SDMX REST cheat sheet <https://github.com/sdmx-twg/sdmx-rest/blob/master/doc/rest_cheat_sheet.pdf>`_.
‘Tolerate’ means that DSSS will respond to them with an SDMX-ML message, although possibly an SDMX-ML ErrorMessage with code 501 indicating the given feature(s) are not implemented.

Thus the code will:

- Respect optional path parts. (done)
- Return appropriate error messages for unavailable resources. (done)
- Filter structures (partial implementation). (done)
- Filter data (partial implementation). (done)
- Return footer or other messages when the response is not fully filtered per path and query parameters. (done)
- Provide documentation in the README for example deployment.
- Include an initial test suite.
- Support, and be tested on, Ubuntu Linux and Python ≥ 3.11

After 1.0, some features that will likely be added include:

- Provide complete documentation.
- Provide a complete test suite.
- Provide logging.
- Support all maintained Python versions, macOS, and Windows.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
