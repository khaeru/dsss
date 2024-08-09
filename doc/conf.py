# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import dsss  # noqa: F401

# -- Project information ---------------------------------------------------------------

project = "DSSS"
copyright = "2024, DSSS contributors"
author = "DSSS contributors"

# -- General configuration -------------------------------------------------------------

templates_path = ["_templates"]
extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
]

rst_prolog = """
.. role:: py(code)
   :language: python
"""

# -- Options for HTML output -----------------------------------------------------------

html_static_path = ["_static"]

# -- Options for sphinx.ext.autosummary ------------------------------------------------

autosummary_generate = True

# -- Options for sphinx.ext.intersphinx ------------------------------------------------

intersphinx_mapping = {
    "py": ("https://docs.python.org/3", None),
    "sdmx": ("https://sdmx1.readthedocs.io/en/stable", None),
}
