"""Main CLI entry point for chanx."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from chanx.client_generator.generator import ClientGenerator


def _run_formatter(output_dir: Path, formatter_cmd: str | None) -> None:
    """
    Run post-processing formatter on generated code.

    Args:
        output_dir: Directory containing generated code
        formatter_cmd: Custom formatter command, or None to auto-detect
    """
    # Determine formatter command
    if formatter_cmd is None:
        # Auto-detect ruff
        if shutil.which("ruff"):
            formatter_cmd = "ruff format"
        else:
            # No formatter available
            return

    click.echo(f"\n🎨 Running formatter: {formatter_cmd}")

    # Parse the command (handle both "ruff format" and just "ruff")
    cmd_parts = formatter_cmd.split()

    try:
        # Run formatter on the output directory
        result = subprocess.run(
            [*cmd_parts, str(output_dir)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            click.echo("   ✓ Code formatted successfully")
        else:
            click.echo(f"   ⚠ Formatter warning: {result.stderr.strip()}", err=True)

    except subprocess.TimeoutExpired:
        click.echo("   ⚠ Formatter timed out (skipped)", err=True)
    except FileNotFoundError:
        click.echo(f"   ⚠ Formatter command not found: {cmd_parts[0]}", err=True)
    except Exception as e:
        click.echo(f"   ⚠ Formatter error: {e}", err=True)


@click.group()
def cli() -> None:
    """Chanx CLI - WebSocket development tools for AsyncAPI."""
    pass


@cli.command(name="generate-client")
@click.option(
    "--schema",
    "-s",
    required=True,
    help="Path or URL to AsyncAPI JSON or YAML schema file",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output directory for generated client code",
)
@click.option(
    "--formatter",
    "-f",
    default=None,
    help="Post-processing formatter command (e.g., 'ruff format', 'black'). If not specified, auto-detects ruff.",
)
@click.option(
    "--no-format",
    is_flag=True,
    default=False,
    help="Skip automatic formatting after generation",
)
@click.option(
    "--no-readme",
    is_flag=True,
    default=False,
    help="Skip README.md generation",
)
@click.option(
    "--clear-output",
    is_flag=True,
    default=False,
    help="Remove entire output directory before generation",
)
@click.option(
    "--override-base",
    is_flag=True,
    default=False,
    help="Regenerate base files even if they already exist",
)
@click.option(
    "--no-clear-channels",
    is_flag=True,
    default=False,
    help="Keep existing channel folders instead of clearing them",
)
def generate_client(
    schema: str,
    output: Path,
    formatter: str | None,
    no_format: bool,
    no_readme: bool,
    clear_output: bool,
    override_base: bool,
    no_clear_channels: bool,
) -> None:
    """
    Generate a type-safe WebSocket client from an AsyncAPI schema.

    This command reads an AsyncAPI 3.0 schema file and generates a complete
    Python WebSocket client package with:

    - Pydantic message models with full type safety
    - Channel-specific client classes with handler stubs
    - send_message() function with typed message union
    - Complete package structure with __init__.py and README.md

    By default, the generated code is automatically formatted with ruff (if available).

    Examples:

        # Basic usage (auto-formats with ruff if available)
        chanx generate-client --schema asyncapi.json --output ./myclient

        # With custom formatter
        chanx generate-client --schema asyncapi.json --output ./myclient --formatter "black"

        # Skip formatting
        chanx generate-client --schema asyncapi.json --output ./myclient --no-format

        # Skip README generation
        chanx generate-client --schema asyncapi.json --output ./myclient --no-readme

        # Clear entire output directory before generation
        chanx generate-client --schema asyncapi.json --output ./myclient --clear-output

        # Force regenerate base files
        chanx generate-client --schema asyncapi.json --output ./myclient --override-base

        # Keep existing channel folders (don't clear them)
        chanx generate-client --schema asyncapi.json --output ./myclient --no-clear-channels

        # With URL
        chanx generate-client --schema https://example.com/api/asyncapi.json --output ./myclient
    """
    click.echo(f"📖 Loading AsyncAPI schema: {schema}")

    try:
        # Generator handles both URLs and file paths
        generator = ClientGenerator(
            schema_path=schema,
            output_dir=str(output),
            generate_readme=not no_readme,
            clear_output=clear_output,
            override_base=override_base,
            clear_channels=not no_clear_channels,
        )

        # Display parsed info
        parsed = generator.schema
        click.echo(f"   Title: {parsed.info.title}")
        click.echo(f"   Version: {parsed.info.version}")
        click.echo(f"   Channels: {len(parsed.channels) if parsed.channels else 0}")
        click.echo(
            f"   Operations: {len(parsed.operations) if parsed.operations else 0}"
        )
        click.echo(
            f"   Schemas: {len(parsed.components.schemas) if parsed.components and parsed.components.schemas else 0}"
        )

        click.echo(f"\n🔧 Generating client code to: {output}")

        # Generate client
        generator.generate()

        click.echo("\n✅ Client generated successfully!")

        # Run post-processing formatter
        if not no_format:
            _run_formatter(output, formatter)

    except FileNotFoundError as e:
        click.echo(f"❌ File not found: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Invalid schema: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
