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

# CHANGELOG.md (written by commitizen) starts at ## under the page's own title.
suppress_warnings = ["myst.header"]

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
html_baseurl = "https://python.chanx.dev/en/latest/"

html_context = {
    "source_type": "github",
    "source_user": "chanx-dev",
    "source_repo": "chanx",
    "source_version": "main",
    "source_docs_path": "/docs/",
}

html_favicon = "_static/brand/favicon.ico"
html_css_files = ["brand/brand.css"]

html_theme_options = {
    "light_logo": "_static/brand/chanx-wordmark.svg",
    "dark_logo": "_static/brand/chanx-wordmark-dark.svg",
    "accent_color": "blue",
    "github_url": "https://github.com/chanx-dev/chanx",
    "nav_links": [
        {"title": "Get started", "url": "introduction"},
        {"title": "Tutorials", "url": "tutorial-django/prerequisites"},
        {"title": "API", "url": "reference/core"},
        {
            "title": "Ecosystem",
            "children": [
                {
                    "title": "chanx-js",
                    "url": "https://js.chanx.dev/",
                    "summary": "TypeScript clients and server",
                },
                {
                    "title": "chanx-kit",
                    "url": "https://kit.chanx.dev/",
                    "summary": "Copy-in WebSocket components",
                },
            ],
        },
    ],
}

# Only strip prompts from shell snippets; Python snippets are copied as written.
copybutton_prompt_text = r"\$ "
copybutton_prompt_is_regexp = True

# Show "method()" rather than "Class.method()" in the on-this-page lists.
toc_object_entries_show_parents = "hide"

ogp_site_url = html_baseurl
ogp_image = "_static/brand/social-card.png"
ogp_image_alt = "Chanx: Typed WebSocket APIs for Python"
ogp_social_cards = {"enable": False}

# Local URLs in tutorials point at the reader's own server.
linkcheck_ignore = [r"http://localhost:\d+", r"quick-start\.html\?framework="]

# Old per-framework quick starts now open the matching tab of the merged page.
redirects = {
    "quick-start-django": "quick-start.html?framework=django",
    "quick-start-fastapi": "quick-start.html?framework=fastapi",
}
