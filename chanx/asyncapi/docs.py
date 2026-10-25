"""
Assets for the AsyncAPI docs page, shared by the Django and FastAPI views.

The defaults pin one `@asyncapi/react-component` release with SRI hashes; point the
URLs at your own static files to serve the page without a third-party CDN.
"""

import json
from html import escape
from typing import Any

ASYNCAPI_UI_VERSION = "3.2.2"
_CDN = f"https://unpkg.com/@asyncapi/react-component@{ASYNCAPI_UI_VERSION}"
DEFAULT_DOCS_JS_URL = f"{_CDN}/browser/standalone/index.js"
DEFAULT_DOCS_CSS_URL = f"{_CDN}/styles/default.min.css"

# A hash only matches its exact file, so it applies to the default URLs alone.
DEFAULT_DOCS_INTEGRITY = {
    DEFAULT_DOCS_JS_URL: (
        "sha384-/OTzBCE2fCs+wXFZecqj96eHeOnof8fcoSA2OVEHTmV/BeGnpOpolyhDGduFU9xE"
    ),
    DEFAULT_DOCS_CSS_URL: (
        "sha384-oo9RoQcacP++XdMX6CjTucTvASEORHX3chFik0/V2kHcsHiVboGyWZztGeq/0bum"
    ),
}


def docs_assets(
    js_url: str | None = None,
    css_url: str | None = None,
    js_integrity: str | None = None,
    css_integrity: str | None = None,
) -> dict[str, str | None]:
    """Resolve the docs page assets, filling in the pinned defaults."""
    js_url = js_url or DEFAULT_DOCS_JS_URL
    css_url = css_url or DEFAULT_DOCS_CSS_URL
    return {
        "js_url": js_url,
        "css_url": css_url,
        "js_integrity": js_integrity or DEFAULT_DOCS_INTEGRITY.get(js_url),
        "css_integrity": css_integrity or DEFAULT_DOCS_INTEGRITY.get(css_url),
    }


def integrity_attrs(integrity: str | None) -> str:
    """The `integrity`/`crossorigin` attributes for an asset tag, if it has a hash."""
    if not integrity:
        return ""
    return f' integrity="{escape(integrity)}" crossorigin="anonymous"'


def schema_script_json(schema: dict[str, Any]) -> str:
    """Serialize the schema for inlining in a <script>, so text can't close the tag."""
    return json.dumps(schema).replace("</", "<\\/")
