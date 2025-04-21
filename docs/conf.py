# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys
from importlib.metadata import version
from pathlib import Path

import django

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../sandbox"))

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"

django.setup()

project = "chanx"
copyright = "2025, Huy Nguyen"
author = "Huy Nguyen"

release = version("chanx")
version = release


sys.path.insert(0, str(Path(__file__).parent.parent))

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "images"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
