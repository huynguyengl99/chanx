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
sys.path.append(os.path.abspath("../sandbox_django"))

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"

django.setup()

project = "Chanx"
copyright = "2025, Huy Nguyen"
author = "Huy Nguyen"

release = version("chanx")
version = release

smartquotes = False

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
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_llms_txt",
    "sphinx_reredirects",
    "sphinxext.opengraph",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "images"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "shibuya"
html_title = "Chanx"
html_static_path = ["_static"]
html_baseurl = "https://chanx.readthedocs.io/en/latest/"

html_context = {
    "source_type": "github",
    "source_user": "huynguyengl99",
    "source_repo": "chanx",
    "source_version": "main",
    "source_docs_path": "/docs/",
}

html_theme_options = {
    "accent_color": "indigo",
    "github_url": "https://github.com/huynguyengl99/chanx",
    "nav_links": [
        {"title": "Get started", "url": "introduction"},
        {"title": "Tutorials", "url": "tutorial-django/prerequisites"},
        {"title": "API", "url": "reference/core"},
        {
            "title": "Ecosystem",
            "children": [
                {
                    "title": "chanx-js",
                    "url": "https://huynguyengl99.github.io/chanx-js/",
                    "summary": "TypeScript clients and server",
                },
                {
                    "title": "chanx-kit",
                    "url": "https://huynguyengl99.github.io/chanx-kit/",
                    "summary": "Copy-in WebSocket components",
                },
            ],
        },
    ],
}

# Only strip prompts from shell snippets; Python snippets are copied as written.
copybutton_prompt_text = r"\$ "
copybutton_prompt_is_regexp = True

ogp_site_url = html_baseurl
ogp_social_cards = {"enable": False}

# Old per-framework quick starts now open the matching tab of the merged page.
redirects = {
    "quick-start-django": "quick-start.html?framework=django",
    "quick-start-fastapi": "quick-start.html?framework=fastapi",
}
