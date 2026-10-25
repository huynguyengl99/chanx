"""Tests for the Django AsyncAPI docs page assets."""

from typing import Any

from chanx.asyncapi.docs import DEFAULT_DOCS_INTEGRITY, DEFAULT_DOCS_JS_URL
from chanx.channels.utils import override_chanx_settings
from chanx.channels.views import _docs_assets


def test_docs_assets_default_to_the_pinned_cdn() -> None:
    assets = _docs_assets()
    assert assets["js_url"] == DEFAULT_DOCS_JS_URL
    assert assets["js_integrity"] == DEFAULT_DOCS_INTEGRITY[DEFAULT_DOCS_JS_URL]


@override_chanx_settings(
    ASYNCAPI_DOCS_JS_URL="asyncapi/index.js",
    ASYNCAPI_DOCS_CSS_URL="https://cdn.example.com/a.css",
    ASYNCAPI_DOCS_CSS_INTEGRITY="sha384-x",
)
def test_docs_assets_resolve_static_paths(settings: Any) -> None:
    settings.STATIC_URL = "/static/"
    assets = _docs_assets()
    assert assets["js_url"] == "/static/asyncapi/index.js"
    assert assets["js_integrity"] is None
    assert assets["css_url"] == "https://cdn.example.com/a.css"
    assert assets["css_integrity"] == "sha384-x"
