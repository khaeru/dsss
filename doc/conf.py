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
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
]

rst_prolog = """
.. role:: py(code)
   :language: python
"""

# -- Options for HTML output -----------------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = "sphinx_book_theme"

html_static_path = ["_static"]

# -- Options for sphinx.ext.autosummary ------------------------------------------------

autosummary_generate = True

# -- Options for sphinx.ext.extlinks ---------------------------------------------------

extlinks = {
    "issue": ("https://github.com/khaeru/dsss/issues/%s", "#%s"),
    "pull": ("https://github.com/khaeru/dsss/pull/%s", "PR #%s"),
    "gh-user": ("https://github.com/%s", "@%s"),
}

# -- Options for sphinx.ext.intersphinx ------------------------------------------------

intersphinx_mapping = {
    "py": ("https://docs.python.org/3", None),
    "sdmx": ("https://sdmx1.readthedocs.io/en/stable", None),
}

# -- Options for sphinx.ext.todo -------------------------------------------------------

todo_include_todos = True
