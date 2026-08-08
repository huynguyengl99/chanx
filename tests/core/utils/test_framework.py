"""Tests for lazy framework resolution."""

from importlib.machinery import ModuleSpec
from importlib.util import find_spec

import pytest
from chanx.utils import framework
from chanx.utils.framework import channel_layer, consumer_base, detect_framework

HAS_FAST_CHANNELS = find_spec("fast_channels") is not None


def test_detects_django_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(framework, "IS_USING_DJANGO", True)

    assert detect_framework() == "channels"


def test_falls_back_to_whichever_is_importable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(framework, "IS_USING_DJANGO", False)

    from collections.abc import Callable

    def only(available: str) -> Callable[[str], ModuleSpec | None]:
        def fake_find_spec(name: str) -> ModuleSpec | None:
            return ModuleSpec(name, None) if name == available else None

        return fake_find_spec

    monkeypatch.setattr(framework, "find_spec", only("fast_channels"))
    assert detect_framework() == "fast_channels"

    monkeypatch.setattr(framework, "find_spec", only("channels"))
    assert detect_framework() == "channels"


def test_neither_installed_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(framework, "IS_USING_DJANGO", False)

    def missing(name: str) -> None:
        return None

    monkeypatch.setattr(framework, "find_spec", missing)

    with pytest.raises(RuntimeError, match="Neither fast-channels nor channels"):
        detect_framework()


def test_consumer_base_resolves_django(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(framework, "IS_USING_DJANGO", True)

    assert consumer_base().__module__ == "chanx.channels.websocket"


@pytest.mark.skipif(not HAS_FAST_CHANNELS, reason="fast-channels not installed")
def test_consumer_base_resolves_fast_channels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(framework, "IS_USING_DJANGO", False)

    assert consumer_base().__module__ == "chanx.fast_channels.websocket"


@pytest.mark.skipif(not HAS_FAST_CHANNELS, reason="fast-channels not installed")
def test_channel_layer_resolves_from_the_active_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fast_channels.layers import InMemoryChannelLayer, register_channel_layer

    monkeypatch.setattr(framework, "IS_USING_DJANGO", False)
    layer = InMemoryChannelLayer()
    register_channel_layer("framework_util_test", layer)

    assert channel_layer("framework_util_test") is layer
