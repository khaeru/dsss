Usage
=====

Run a local server
------------------

1. Install the package and `uvicorn <https://www.starlette.io/#installation>`_ or another ASGI server::

    pip install dsss uvicorn

2. Indicate the directory containing stored structures and data::

    export DSSS_STORE=/path/to/store

   This directory should be laid out as a :class:`.StructuredFileStore`.

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
