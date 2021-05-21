``dsss``: a dead-simple SDMX server
***********************************

A rudimentary implementation of the `SDMX REST web service <https://github.com/sdmx-twg/sdmx-rest>`_ standard.

Usage
=====

To run a debug server::

  git clone git@github.com:khaeru/dsss.git && cd dsss
  pip install --editable .
  FLASK_APP=. dsss debug
