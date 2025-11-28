"""Snapshot tests for generated client code.

These tests ensure that the generated client code matches the expected output
exactly. This helps catch unintended changes in code generation.
"""

import subprocess
from pathlib import Path
from unittest import TestCase

import pytest
from chanx.client_generator.generator import ClientGenerator


class TestGeneratedClientSnapshot(TestCase):
    """Snapshot tests for generated client code."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test fixtures."""
        self.tmp_path = tmp_path
        self.fixtures_dir = (
            Path(__file__).parent.parent / "fixtures" / "client_generation"
        )
        self.schema_path = self.fixtures_dir / "schema.json"
        self.expected_output_dir = self.fixtures_dir / "expected_output"

    def _generate_and_format(self, output_dir: Path) -> None:
        """Generate client code and format it."""
        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
        )
        generator.generate()

        # Format the output to match expected output (which is formatted)
        # Use ruff and black directly since scripts/lint.sh only works on repo root
        subprocess.run(
            ["ruff", "check", str(output_dir), "--fix"],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["black", str(output_dir)],
            capture_output=True,
            check=False,
        )

    def test_chat_client_snapshot(self) -> None:
        """Test that generated chat client matches expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare chat client
        generated_file = output_dir / "chat" / "client.py"
        expected_file = self.expected_output_dir / "chat" / "client.py"

        assert generated_file.exists(), "Generated chat client file not found"
        assert expected_file.exists(), "Expected chat client file not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert generated_content == expected_content, "Chat client content mismatch"

    def test_chat_messages_snapshot(self) -> None:
        """Test that generated chat messages match expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare chat messages
        generated_file = output_dir / "chat" / "messages.py"
        expected_file = self.expected_output_dir / "chat" / "messages.py"

        assert generated_file.exists(), "Generated chat messages file not found"
        assert expected_file.exists(), "Expected chat messages file not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert generated_content == expected_content, "Chat messages content mismatch"

    def test_shared_messages_snapshot(self) -> None:
        """Test that generated shared messages match expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare shared messages
        generated_file = output_dir / "shared" / "messages.py"
        expected_file = self.expected_output_dir / "shared" / "messages.py"

        assert generated_file.exists(), "Generated shared messages file not found"
        assert expected_file.exists(), "Expected shared messages file not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert generated_content == expected_content, "Shared messages content mismatch"

    def test_package_init_snapshot(self) -> None:
        """Test that generated package __init__.py matches expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare package init
        generated_file = output_dir / "__init__.py"
        expected_file = self.expected_output_dir / "__init__.py"

        assert generated_file.exists(), "Generated package __init__.py not found"
        assert expected_file.exists(), "Expected package __init__.py not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert (
            generated_content == expected_content
        ), "Package __init__.py content mismatch"

    def test_room_chat_client_with_parameters_snapshot(self) -> None:
        """Test that generated room_chat client with path parameters matches expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare room_chat client (has path parameters)
        generated_file = output_dir / "room_chat" / "client.py"
        expected_file = self.expected_output_dir / "room_chat" / "client.py"

        assert generated_file.exists(), "Generated room_chat client file not found"
        assert expected_file.exists(), "Expected room_chat client file not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert (
            generated_content == expected_content
        ), "Room chat client content mismatch"

    def test_all_channel_files_snapshot(self) -> None:
        """Test that all channel files match expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        channels = [
            "chat",
            "reliable_chat",
            "notifications",
            "analytics",
            "system",
            "background_jobs",
            "room_chat",
        ]

        for channel in channels:
            # Check client.py
            generated_client = output_dir / channel / "client.py"
            expected_client = self.expected_output_dir / channel / "client.py"

            assert generated_client.exists(), f"Generated {channel} client not found"
            assert expected_client.exists(), f"Expected {channel} client not found"

            generated_content = generated_client.read_text(encoding="utf-8")
            expected_content = expected_client.read_text(encoding="utf-8")

            assert (
                generated_content == expected_content
            ), f"{channel} client content mismatch"

            # Check messages.py
            generated_messages = output_dir / channel / "messages.py"
            expected_messages = self.expected_output_dir / channel / "messages.py"

            assert (
                generated_messages.exists()
            ), f"Generated {channel} messages not found"
            assert expected_messages.exists(), f"Expected {channel} messages not found"

            generated_content = generated_messages.read_text(encoding="utf-8")
            expected_content = expected_messages.read_text(encoding="utf-8")

            assert (
                generated_content == expected_content
            ), f"{channel} messages content mismatch"

            # Check __init__.py
            generated_init = output_dir / channel / "__init__.py"
            expected_init = self.expected_output_dir / channel / "__init__.py"

            assert generated_init.exists(), f"Generated {channel} __init__ not found"
            assert expected_init.exists(), f"Expected {channel} __init__ not found"

            generated_content = generated_init.read_text(encoding="utf-8")
            expected_content = expected_init.read_text(encoding="utf-8")

            assert (
                generated_content == expected_content
            ), f"{channel} __init__ content mismatch"

    def test_base_client_snapshot(self) -> None:
        """Test that base client files match expected output."""
        output_dir = self.tmp_path / "output"
        self._generate_and_format(output_dir)

        # Compare base client
        generated_file = output_dir / "base" / "client.py"
        expected_file = self.expected_output_dir / "base" / "client.py"

        assert generated_file.exists(), "Generated base client file not found"
        assert expected_file.exists(), "Expected base client file not found"

        generated_content = generated_file.read_text(encoding="utf-8")
        expected_content = expected_file.read_text(encoding="utf-8")

        assert generated_content == expected_content, "Base client content mismatch"
