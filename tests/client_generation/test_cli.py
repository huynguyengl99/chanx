"""Tests for the CLI generate-client command."""

from pathlib import Path
from unittest import TestCase

import pytest
from chanx.cli.main import cli
from click.testing import CliRunner


class TestCLIGenerateClient(TestCase):
    """Test cases for the generate-client CLI command."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test fixtures."""
        self.tmp_path = tmp_path
        self.fixtures_dir = (
            Path(__file__).parent.parent / "fixtures" / "client_generation"
        )
        self.schema_path = self.fixtures_dir / "schema.json"
        self.runner = CliRunner()

    def test_generate_client_basic(self) -> None:
        """Test basic client generation via CLI."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-format",  # Skip formatting for faster tests
            ],
        )

        assert result.exit_code == 0, f"CLI failed with output: {result.output}"
        assert "Client generated successfully!" in result.output
        assert output_dir.exists()
        assert (output_dir / "__init__.py").exists()

    def test_generate_client_with_readme(self) -> None:
        """Test client generation with README."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-format",
            ],
        )

        assert result.exit_code == 0
        assert (output_dir / "README.md").exists()

    def test_generate_client_without_readme(self) -> None:
        """Test client generation without README."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-readme",
                "--no-format",
            ],
        )

        assert result.exit_code == 0
        assert not (output_dir / "README.md").exists()

    def test_generate_client_missing_schema(self) -> None:
        """Test that CLI fails with missing schema file."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                "/nonexistent/schema.json",
                "--output",
                str(output_dir),
            ],
        )

        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_generate_client_displays_schema_info(self) -> None:
        """Test that CLI displays schema information."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-format",
            ],
        )

        assert result.exit_code == 0
        assert "FastAPI AsyncAPI documentation" in result.output
        assert "Version: 1.0.0" in result.output
        assert "Channels:" in result.output
        assert "Operations:" in result.output
        assert "Schemas:" in result.output

    def test_generate_client_with_decamelize(self) -> None:
        """Test client generation with decamelize option."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--decamelize",
                "--no-format",
            ],
        )

        assert result.exit_code == 0
        assert output_dir.exists()

    def test_generate_client_required_options(self) -> None:
        """Test that required options are enforced."""
        # Missing --schema
        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--output",
                str(self.tmp_path / "client"),
            ],
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

        # Missing --output
        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
            ],
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_generate_client_help(self) -> None:
        """Test that help message is displayed."""
        result = self.runner.invoke(cli, ["generate-client", "--help"])

        assert result.exit_code == 0
        assert "Generate a type-safe WebSocket client" in result.output
        assert "--schema" in result.output
        assert "--output" in result.output
        assert "--decamelize" in result.output
        assert "--formatter" in result.output
        assert "--no-format" in result.output
        assert "--no-readme" in result.output

    def test_generate_client_with_custom_formatter(self) -> None:
        """Test client generation with custom formatter command."""
        output_dir = self.tmp_path / "client"

        # Use 'echo' as a dummy formatter that won't fail
        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--formatter",
                "echo",
            ],
        )

        assert result.exit_code == 0
        assert "Running formatter: echo" in result.output

    def test_generate_client_formatter_not_found(self) -> None:
        """Test that CLI handles formatter not found gracefully."""
        output_dir = self.tmp_path / "client"

        result = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--formatter",
                "nonexistent_formatter_command",
            ],
        )

        # Should still succeed even if formatter fails
        assert result.exit_code == 0
        assert "Client generated successfully!" in result.output
        assert (
            "Formatter command not found" in result.output
            or "Formatter" in result.output
        )

    def test_generate_client_overwrites_existing_directory(self) -> None:
        """Test that generating to existing directory overwrites it."""
        output_dir = self.tmp_path / "client"

        # Generate once
        result1 = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-format",
            ],
        )
        assert result1.exit_code == 0

        # Create a dummy file
        dummy_file = output_dir / "dummy.txt"
        dummy_file.write_text("This should be removed")

        # Generate again
        result2 = self.runner.invoke(
            cli,
            [
                "generate-client",
                "--schema",
                str(self.schema_path),
                "--output",
                str(output_dir),
                "--no-format",
            ],
        )
        assert result2.exit_code == 0

        # Dummy file should be removed
        assert not dummy_file.exists()

    def test_generate_client_formatter_timeout(self) -> None:
        """Test that formatter timeout is handled gracefully."""
        import subprocess
        from unittest.mock import patch

        output_dir = self.tmp_path / "client"

        # Patch subprocess.run to raise TimeoutExpired
        with patch("chanx.cli.main.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("formatter", 30)

            result = self.runner.invoke(
                cli,
                [
                    "generate-client",
                    "--schema",
                    str(self.schema_path),
                    "--output",
                    str(output_dir),
                    "--formatter",
                    "slow_formatter",
                ],
            )

        # Should still succeed despite formatter timeout
        assert result.exit_code == 0
        assert "Formatter timed out" in result.output

    def test_generate_client_formatter_error(self) -> None:
        """Test that formatter errors are handled gracefully."""
        from unittest.mock import patch

        output_dir = self.tmp_path / "client"

        # Patch subprocess.run to raise an exception
        with patch("chanx.cli.main.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            result = self.runner.invoke(
                cli,
                [
                    "generate-client",
                    "--schema",
                    str(self.schema_path),
                    "--output",
                    str(output_dir),
                    "--formatter",
                    "error_formatter",
                ],
            )

        # Should still succeed despite formatter error
        assert result.exit_code == 0
        assert "Formatter error" in result.output

    def test_generate_client_formatter_warning(self) -> None:
        """Test that formatter warnings are displayed."""
        from unittest.mock import Mock, patch

        output_dir = self.tmp_path / "client"

        # Patch subprocess.run to return non-zero exit code
        with patch("chanx.cli.main.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Warning: some files not formatted"
            mock_run.return_value = mock_result

            result = self.runner.invoke(
                cli,
                [
                    "generate-client",
                    "--schema",
                    str(self.schema_path),
                    "--output",
                    str(output_dir),
                    "--formatter",
                    "warning_formatter",
                ],
            )

        assert result.exit_code == 0
        assert "Formatter warning" in result.output

    def test_generate_client_auto_detect_ruff(self) -> None:
        """Test that ruff is auto-detected when no formatter is specified."""
        from unittest.mock import Mock, patch

        output_dir = self.tmp_path / "client"

        # Mock shutil.which to find ruff
        with patch("chanx.cli.main.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/ruff"

            with patch("chanx.cli.main.subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                result = self.runner.invoke(
                    cli,
                    [
                        "generate-client",
                        "--schema",
                        str(self.schema_path),
                        "--output",
                        str(output_dir),
                    ],
                )

        assert result.exit_code == 0
        assert "ruff format" in result.output

    def test_generate_client_no_formatter_available(self) -> None:
        """Test generation when no formatter is available."""
        from unittest.mock import patch

        output_dir = self.tmp_path / "client"

        # Mock shutil.which to not find any formatter
        with patch("chanx.cli.main.shutil.which") as mock_which:
            mock_which.return_value = None

            result = self.runner.invoke(
                cli,
                [
                    "generate-client",
                    "--schema",
                    str(self.schema_path),
                    "--output",
                    str(output_dir),
                ],
            )

        assert result.exit_code == 0
        # Should not attempt formatting
        assert "Running formatter" not in result.output
