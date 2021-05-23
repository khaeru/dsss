``dsss``: a dead-simple SDMX server
***********************************

A rudimentary implementation of the `SDMX REST web service <https://github.com/sdmx-twg/sdmx-rest>`_ standard.

This code is developed mainly as an aid for prototyping and testing other code that generates SDMX or relies on SDMX REST web services being available.
It is not intended and likely not ready for production use.

Run a local server
==================

1. ``git clone git@github.com:khaeru/dsss.git && cd dsss``

2. Create a directory ``data`` in the repo root and add files to be used to serve requests:

   - 1 or more files containing SDMX structure messages, named e.g. ``AGENCY-structure.xml``, where AGENCY is the ID of an agency that is an SDMX data provider.
     This single file contains all possible structures provided by AGENCY, to be filtered per the request.
   - 0 or more files containing SDMX (meta)data messages, named e.g. ``AGENCY:FLOW1-data.xml`` or ``AGENCY:FLOW2-metadata.xml``, where FLOW1/2 is the ID of a (meta)data flow definition, and -data or -metadata indicates the contents.
     Each file contains all possible (meta)data within the given (meta)dataflow, to be filtered per the request.

3. Run::

    pip install --editable .
    FLASK_APP=. dsss debug

   The output will include a line like:

    * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

4. Open a browser or use `curl` on the terminal to query this server::

    curl -i http://127.0.0.1:5000/codelist/AGENCY/CL_FOO/latest/all?detail=full

Deploy to Google App Engine
===========================

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

For a 1.0 release, the code will _tolerate_ all the queries possible using the `SDMX REST cheat sheet <https://raw.githubusercontent.com/sdmx-twg/sdmx-rest/master/v2_1/ws/rest/docs/rest_cheat_sheet.pdf>`_.
Thus:

- [x] Respect optional path parts.
- [x] Return appropriate error messages for unavailable resources.
- [x] Filter structures (partial implementation).
- [ ] Filter data (partial implementation).
- [x] Return footer or other messages when the response is not fully filtered per path and query parameters.
- [x] Provide `dsss`-specific instructions for deployment, with reference to the `Flask docs <https://flask.palletsprojects.com/en/2.0.x/deploying/>`_.

After 1.0:

- Provide a complete test suite.
- Use Flask's `logging capabilities <https://flask.palletsprojects.com/en/2.0.x/logging/>`_.
- Integrate URL construction in `sdmx1 <https://github.com/khaeru/sdmx`_.

  Flask provides the `url_for() <https://flask.palletsprojects.com/en/2.0.x/api/#flask.url_for>`_ function and underying machinery to construct URLs within the routing scheme for an application.
  This mirrors the code in `sdmx1.Client._request_from_args() <https://github.com/khaeru/sdmx/blob/main/sdmx/client.py#L161>`_, about 100 lines.
  Consider ways to provide common code in ``sdmx1`` and reuse that code in DSSS, or vice versa.
