"""Tests for the AsyncAPI docs page assets."""

import json

from chanx.asyncapi.docs import (
    DEFAULT_DOCS_CSS_URL,
    DEFAULT_DOCS_INTEGRITY,
    DEFAULT_DOCS_JS_URL,
    docs_assets,
    integrity_attrs,
    schema_script_json,
)


def test_defaults_are_pinned_with_integrity() -> None:
    assets = docs_assets()
    assert assets["js_url"] == DEFAULT_DOCS_JS_URL
    assert assets["css_url"] == DEFAULT_DOCS_CSS_URL
    assert "@latest" not in DEFAULT_DOCS_JS_URL
    assert assets["js_integrity"] == DEFAULT_DOCS_INTEGRITY[DEFAULT_DOCS_JS_URL]
    assert assets["css_integrity"] == DEFAULT_DOCS_INTEGRITY[DEFAULT_DOCS_CSS_URL]


def test_custom_url_drops_the_pinned_hash() -> None:
    assets = docs_assets(js_url="/static/asyncapi.js", css_integrity="sha384-x")
    assert assets["js_url"] == "/static/asyncapi.js"
    assert assets["js_integrity"] is None
    assert assets["css_url"] == DEFAULT_DOCS_CSS_URL
    assert assets["css_integrity"] == "sha384-x"


def test_integrity_attrs() -> None:
    assert integrity_attrs(None) == ""
    assert integrity_attrs("sha384-x") == (
        ' integrity="sha384-x" crossorigin="anonymous"'
    )


def test_schema_script_json_cannot_close_the_script() -> None:
    schema = {"info": {"description": "</script><script>alert(1)</script>"}}
    serialized = schema_script_json(schema)
    assert "</" not in serialized
    assert json.loads(serialized) == schema
