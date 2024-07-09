DSSS: a dead-simple SDMX server
*******************************

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api
   whatsnew

Usage
=====

Run a local server
------------------

1. Install the package and `uvicorn <https://www.starlette.io/#installation>`_ or another ASGI server::

    git clone git@github.com:khaeru/dsss.git
    cd dsss
    pip install . uvicorn

   The package is not yet published on PyPI.

2. Indicate the directory containing stored structures and data::

    export DSSS_STORE=/path/to/store

   This directory should be laid out as a ``StructuredFileStore`` (not yet documented).

3. Run::

    uvicorn --factory dsss:build_app

   The output will include a line like:

    * Running on http://127.0.0.1:8000/ (Press CTRL+C to quit)

4. Open a browser or use `curl` on the terminal to query this server::

    curl -i http://127.0.0.1:5000/codelist/AGENCY/CL_FOO/latest/all?detail=full

Deploy to Google App Engine
---------------------------

Not currently supported.

..
   At minimum, this requires a file ``app.yaml`` containing:

   .. code-block:: yaml

      runtime: python39
      entrypoint: gunicorn -b :$PORT dsss:serve

   and a file ``requirements.txt`` containing:

   .. code-block::

      git+git://github.com/khaeru/dsss#egg=dsss
      gunicorn

   Then (with the `Google Cloud SDK <https://cloud.google.com/sdk/docs/install>`_ installed and configured) run::

       gcloud app deploy

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
