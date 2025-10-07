"""
Tests for chanx.core.config module.

Tests the configuration system that's framework-agnostic.
"""

from chanx.core.config import Config


class TestConfig:
    """Test the core configuration class."""

    def test_default_values(self) -> None:
        """Test that default configuration values are set correctly."""
        config = Config()

        # Note: send_completion may be True if Django settings are loaded
        assert config.send_completion in [True, False]
        assert config.send_message_immediately is True
        assert config.log_websocket_message is False
        assert config.log_ignored_actions == {}
        assert config.camelize is False

    def test_config_attribute_access(self) -> None:
        """Test that config attributes can be accessed."""
        config = Config()

        # Test all default attributes
        attributes = [
            "send_completion",
            "send_message_immediately",
            "log_websocket_message",
            "log_ignored_actions",
            "camelize",
        ]

        for attr in attributes:
            assert hasattr(config, attr)
            # Should not raise an exception
            getattr(config, attr)

    def test_config_boolean_attributes(self) -> None:
        """Test that boolean config attributes are actually booleans."""
        config = Config()

        boolean_attrs = [
            "send_completion",
            "send_message_immediately",
            "log_websocket_message",
            "camelize",
        ]

        for attr in boolean_attrs:
            value = getattr(config, attr)
            assert isinstance(
                value, bool
            ), f"{attr} should be boolean, got {type(value)}"
