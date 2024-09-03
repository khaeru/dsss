DSSS: a dead-simple SDMX server
*******************************

.. image:: https://img.shields.io/pypi/v/dsss.svg
   :target: https://pypi.org/project/dsss
   :alt: PyPI version badge
.. image:: https://readthedocs.org/projects/dsss/badge/?version=latest
   :target: https://dsss.readthedocs.io/en/latest
   :alt: Documentation status badge
.. image:: https://codecov.io/gh/khaeru/dsss/graph/badge.svg?token=IL5RTND3E7
   :target: https://codecov.io/gh/khaeru/dsss
   :alt: Codecov test coverage badge
.. image:: https://github.com/khaeru/dsss/actions/workflows/pytest.yaml/badge.svg
   :target: https://github.com/khaeru/dsss/actions/workflows/pytest.yaml
   :alt: Status badge for the "pytest" continuous testing workflow

A rudimentary implementation of the `SDMX REST web service <https://github.com/sdmx-twg/sdmx-rest>`_ standard.

This package is developed mainly as an aid for prototyping and testing other code that generates SDMX or relies on SDMX REST web services being available.
It is not currently intended and likely not ready for production use.

The package depends only on:

- `sdmx1 <https://github.com/khaeru/sdmx>`_ —for the SDMX Information Model, file formats, URLs, URNs, and more.
- `starlette <https://www.starlette.io>`_ —as a base web service framework.

It provides a :class:`.Store` class and subclasses for storing the structures and data to be served by an instance.

On this page:

.. contents::
   :local:
   :backlinks: none

On other pages:

.. toctree::
   :maxdepth: 1

   usage
   api
   whatsnew

Roadmap
=======

After 1.0, some features that will likely be added include:

- Provide complete documentation, including for cloud deployment.
- Provide logging.
- Support additional maintained Python versions prior to Python 3.11.
- Support macOS and Windows (low priority).

The following is a list of TODOs appearing throughout this documentation:

.. todolist::

License
=======

Copyright 2014–2024, `dsss developers <https://github.com/khaeru/dsss/graphs/contributors>`_

Licensed under the GNU Affero General Public License, Version 3.0 (the “License”); you may not use these files except in compliance with the License.
You may obtain a copy of the License:

- from the file LICENSE included with the source code, or
- at https://www.gnu.org/licenses/agpl-3.0.en.html


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
