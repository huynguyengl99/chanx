"""Schema loader for AsyncAPI documents from various sources."""

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml


class SchemaLoader:
    """Load AsyncAPI schemas from files or URLs."""

    @staticmethod
    def load(path_or_url: str) -> dict[str, Any]:
        """
        Load AsyncAPI schema from file path or URL.

        Supports both JSON and YAML formats. Automatically detects whether
        the input is a URL or file path and handles accordingly.

        Args:
            path_or_url: File path or HTTP(S) URL to the schema

        Returns:
            Dictionary containing the parsed schema

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported or URL fetch fails
        """
        # Check if it's a URL
        if SchemaLoader._is_url(path_or_url):
            return SchemaLoader._load_from_url(path_or_url)
        else:
            return SchemaLoader._load_from_file(path_or_url)

    @staticmethod
    def _is_url(path_or_url: str) -> bool:
        """Check if the input is a URL."""
        try:
            result = urlparse(path_or_url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def _load_from_url(url: str) -> dict[str, Any]:
        """
        Load AsyncAPI schema from HTTP(S) URL.

        Args:
            url: HTTP(S) URL to the schema

        Returns:
            Dictionary containing the parsed schema

        Raises:
            ValueError: If URL fetch fails or content is invalid
        """
        try:
            import httpx
        except ImportError as e:
            raise ValueError(
                "httpx is required to load schemas from URLs. "
                "Install it with: pip install httpx"
            ) from e

        try:
            response = httpx.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            content = response.text

            # Try to determine format from content-type or URL
            content_type = response.headers.get("content-type", "")
            if "yaml" in content_type or url.endswith((".yaml", ".yml")):
                return SchemaLoader._load_yaml(content)
            elif "json" in content_type or url.endswith(".json"):
                return SchemaLoader._load_json(content)
            else:
                # Auto-detect
                return SchemaLoader._load_auto(content, url)

        except httpx.HTTPStatusError as e:
            raise ValueError(
                f"HTTP error loading schema from {url}: "
                f"{e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ValueError(f"Request error loading schema from {url}: {e}") from e

    @staticmethod
    def _load_from_file(path: str) -> dict[str, Any]:
        """
        Load AsyncAPI schema from file path.

        Args:
            path: File path to the schema

        Returns:
            Dictionary containing the parsed schema

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        schema_path = Path(path)

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        content = schema_path.read_text(encoding="utf-8")

        # Determine format from extension
        suffix = schema_path.suffix.lower()

        if suffix == ".json":
            return SchemaLoader._load_json(content)
        elif suffix in [".yaml", ".yml"]:
            return SchemaLoader._load_yaml(content)
        else:
            # Try to auto-detect
            return SchemaLoader._load_auto(content, path)

    @staticmethod
    def _load_json(content: str) -> dict[str, Any]:
        """Load JSON content."""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Schema must be a JSON object")
            return cast(dict[str, Any], data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e

    @staticmethod
    def _load_yaml(content: str) -> dict[str, Any]:
        """Load YAML content."""
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise ValueError("Schema must be a YAML object")
            return cast(dict[str, Any], data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}") from e

    @staticmethod
    def _load_auto(content: str, path: str) -> dict[str, Any]:
        """Auto-detect and load content."""
        # Try JSON first
        try:
            return SchemaLoader._load_json(content)
        except ValueError:
            pass

        # Try YAML
        try:
            return SchemaLoader._load_yaml(content)
        except ValueError:
            pass

        raise ValueError(
            f"Could not parse schema file: {path}. "
            "Supported formats: .json, .yaml, .yml"
        )
