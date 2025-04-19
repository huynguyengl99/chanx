from unittest.mock import patch

from django.test import TestCase

import pytest
from chanx.testing import WebsocketTestCase


class TestWebsocketTesting(TestCase):
    def test_ws_path_not_set(self):
        with pytest.raises(
            AttributeError, match=r"ws_path is not set in ImplementedWebsocketTestCase"
        ):

            class ImplementedWebsocketTestCase(WebsocketTestCase):
                pass

            test_case = ImplementedWebsocketTestCase()
            test_case.setUp()
            test_case.create_communicator()

    def test_websocket_application_not_found(self):
        # Mock get_websocket_application to return None
        with patch("chanx.testing.get_websocket_application", return_value=None):
            # Define a test class with ws_path set
            class TestWebsocketCase(WebsocketTestCase):
                ws_path = "/test/"

            # Try to instantiate the class, which should trigger the error
            with pytest.raises(
                ValueError, match=r"Could not obtain a WebSocket application"
            ):
                TestWebsocketCase()
