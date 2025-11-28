"""Tests for the ClientGenerator class."""

from pathlib import Path
from unittest import TestCase

import pytest
from chanx.client_generator.generator import ClientGenerator


class TestClientGenerator(TestCase):
    """Test cases for ClientGenerator."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test fixtures."""
        self.tmp_path = tmp_path
        self.fixtures_dir = (
            Path(__file__).parent.parent / "fixtures" / "client_generation"
        )
        self.schema_path = self.fixtures_dir / "schema.json"
        self.expected_output_dir = self.fixtures_dir / "expected_output"

    def test_generator_initialization(self) -> None:
        """Test that the generator initializes correctly."""
        output_dir = self.tmp_path / "output"

        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
            decamelize=False,
            generate_readme=True,
        )

        assert generator.schema_path == str(self.schema_path)
        assert generator.output_dir == output_dir
        assert generator.decamelize is False
        assert generator.generate_readme is True
        assert generator.schema.info.title == "FastAPI AsyncAPI documentation"
        assert generator.schema.info.version == "1.0.0"

    def test_generator_with_invalid_schema_path(self) -> None:
        """Test that generator raises error with invalid schema path."""
        with pytest.raises(FileNotFoundError):
            ClientGenerator(
                schema_path="/nonexistent/path/schema.json",
                output_dir=str(self.tmp_path / "output"),
            )

    def test_generate_creates_directory_structure(self) -> None:
        """Test that generate() creates the expected directory structure."""
        output_dir = self.tmp_path / "output"

        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
        )
        generator.generate()

        # Check main package structure
        assert output_dir.exists()
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "README.md").exists()
        assert (output_dir / "base").exists()
        assert (output_dir / "base" / "client.py").exists()
        assert (output_dir / "shared").exists()
        assert (output_dir / "shared" / "messages.py").exists()

        # Check channel directories
        expected_channels = [
            "chat",
            "reliable_chat",
            "notifications",
            "analytics",
            "system",
            "background_jobs",
            "room_chat",
        ]
        for channel in expected_channels:
            assert (output_dir / channel).exists()
            assert (output_dir / channel / "__init__.py").exists()
            assert (output_dir / channel / "client.py").exists()
            assert (output_dir / channel / "messages.py").exists()

    def test_generate_without_readme(self) -> None:
        """Test that README is not generated when generate_readme=False."""
        output_dir = self.tmp_path / "output"

        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
            generate_readme=False,
        )
        generator.generate()

        assert not (output_dir / "README.md").exists()

    def test_generated_output_matches_expected(self) -> None:
        """Test that generated output matches the expected output (snapshot test)."""
        import subprocess

        output_dir = self.tmp_path / "output"

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

        # Compare all generated files with expected output
        # Exclude README.md from comparison as it may have dynamic content
        self._compare_directories(
            output_dir, self.expected_output_dir, exclude=["README.md"]
        )

    def test_shared_messages_detection(self) -> None:
        """Test that shared messages are correctly detected."""
        output_dir = self.tmp_path / "output"

        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
        )

        # PingMessage and PongMessage should be shared across multiple channels
        # The title is on the payload (schema), not the MessageObject
        shared_message_titles = {
            msg.payload.title for msg in generator.shared_messages if msg.payload
        }
        assert "PingMessage" in shared_message_titles
        assert "PongMessage" in shared_message_titles

    def test_channel_messages_extraction(self) -> None:
        """Test that channel messages are correctly extracted."""
        output_dir = self.tmp_path / "output"

        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
        )

        # Check that all channels have messages
        assert "chat" in generator.channel_messages
        assert "reliable_chat" in generator.channel_messages

        # Check that chat channel has incoming and outgoing messages
        incoming, outgoing = generator.channel_messages["chat"]
        assert len(incoming) > 0
        assert len(outgoing) > 0

    def test_regeneration_cleans_output_directory(self) -> None:
        """Test that regenerating cleans the output directory first."""
        output_dir = self.tmp_path / "output"

        # Generate once
        generator = ClientGenerator(
            schema_path=str(self.schema_path),
            output_dir=str(output_dir),
        )
        generator.generate()

        # Create a dummy file
        dummy_file = output_dir / "dummy.txt"
        dummy_file.write_text("This should be removed")
        assert dummy_file.exists()

        # Generate again
        generator.generate()

        # Dummy file should be removed
        assert not dummy_file.exists()

    def _compare_directories(
        self, dir1: Path, dir2: Path, exclude: list[str] | None = None
    ) -> None:
        """
        Recursively compare two directories.

        Args:
            dir1: First directory to compare
            dir2: Second directory to compare
            exclude: List of filenames to exclude from comparison
        """
        exclude = exclude or []

        # Get all files in both directories
        files1: set[Path] = set()
        files2: set[Path] = set()

        for f in dir1.rglob("*"):
            # Skip __pycache__ directories and excluded files
            if "__pycache__" in f.parts:
                continue
            if f.is_file() and f.name not in exclude:
                files1.add(f.relative_to(dir1))

        for f in dir2.rglob("*"):
            # Skip __pycache__ directories and excluded files
            if "__pycache__" in f.parts:
                continue
            if f.is_file() and f.name not in exclude:
                files2.add(f.relative_to(dir2))

        # Check that all files exist in both directories
        assert (
            files1 == files2
        ), f"File mismatch:\nOnly in {dir1}: {files1 - files2}\nOnly in {dir2}: {files2 - files1}"

        # Compare file contents
        file_path: Path
        for file_path in files1:
            file1: Path = dir1 / file_path
            file2: Path = dir2 / file_path

            content1: str = file1.read_text(encoding="utf-8")
            content2: str = file2.read_text(encoding="utf-8")

            assert content1 == content2, f"Content mismatch in {file_path}"
