``dsss``: a dead-simple SDMX server
***********************************
|gha|

.. |gha| image:: https://github.com/khaeru/dsss/actions/workflows/pytest.yaml/badge.svg
   :target: https://github.com/khaeru/dsss/actions/workflows/pytest.yaml
   :alt: Status badge for the "pytest" continuous testing workflow

A rudimentary implementation of the `SDMX REST web service <https://github.com/sdmx-twg/sdmx-rest>`_ standard.

This code is developed mainly as an aid for prototyping and testing other code that generates SDMX or relies on SDMX REST web services being available.
It is not currently intended and likely not ready for production use.

Implementation
==============

The package depends only on:

- `sdmx1 <https://github.com/khaeru/sdmx>`_ —for the SDMX Information Model, file formats, URLs, URNs, and more.
- `starlette <https://www.starlette.io>`_ —as a base web service framework.

It provides a ``Store`` class and subclasses for storing the structures and data to be served by an instance.


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
===========================

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

After 1.0, some features to be added include:

- Provide complete documentation.
- Provide a complete test suite.
- Provide logging.

License
=======

Copyright 2014–2024, `dsss developers <https://github.com/khaeru/dsss/graphs/contributors>`_

Licensed under the GNU General Public License, Version 3.0 (the “License”); you may not use these files except in compliance with the License.
You may obtain a copy of the License:

- from the file LICENSE included with the source code, or
- at https://www.gnu.org/licenses/gpl-3.0.en.html
