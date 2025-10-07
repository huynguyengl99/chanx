# Contributing to chanx

Thank you for your interest in contributing to chanx! This guide will help you set up the development environment and
understand the tools and processes used in this project.

## Prerequisites

Before starting development, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python package management
- Python 3.11+ (project supports 3.11, 3.12, and 3.13)

## Install the library for development

### Setting up your environment

Create your own virtual environment and activate it:

```bash
uv venv
source .venv/bin/activate
```

Then use uv to install all dev packages:
```bash
uv sync --all-extras
```

### Using tox for complete environment testing

For testing across multiple Python versions and configurations, we use tox:

```bash
# Install tox following the official documentation
# https://tox.wiki/en/latest/installation.html
uv tool install tox

# Run tests on all supported Python versions
tox

# Run tests for a specific environment
tox -e py311

# Run only the linting checks
tox -e lint

# Run test coverage
tox -e coverage
```

## Understanding the project structure

The project has several key directories for development and testing:

### Sandbox Directories
- **`sandbox_django`** - Django integration sandbox for development and testing
- **`sandbox_fastapi`** - FastAPI integration sandbox for development and testing

These serve two main purposes:

1. **Testing Environment**: Write and run tests for the package
   - Contains test applications and configurations
   - Used with pytest to validate package functionality

2. **Development Playground**: Run as Django/FastAPI applications to test features
   - Run Django commands like `makemigrations` and `migrate`
   - Interact with API endpoints for manual testing
   - Test UI components and integrations

### Test Directories
- **`tests/core`** - Core functionality tests
- **`tests/ext/channels`** - Django Channels extension tests
- **`tests/ext/fast_channels`** - FastAPI and other framework extension tests

## Prepare the environment

Before working with the sandbox or running tests, ensure:
- Docker is running
- Run `docker compose up -d` to create necessary databases/services (Redis and PostgreSQL) in detached mode

## Working with the sandbox projects

### Django Sandbox Setup

```bash
# Apply database migrations
python sandbox_django/manage.py migrate

# Create a superuser for accessing the admin interface
python sandbox_django/manage.py createsuperuser

# Run Django development server
python sandbox_django/manage.py runserver
```

Once the Django server is running, you can access:
- **Admin interface**: http://localhost:8000/admin/
- **Login/Registration**: http://localhost:8000/login
- **Chat (Assistants/Discussions)**: http://localhost:8000/chat (requires authentication)
- Test API endpoints and verify package functionality

#### Django Development Commands

```bash
# Create migrations for your changes
python sandbox_django/manage.py makemigrations
```

### FastAPI Sandbox Setup

```bash
# Start both FastAPI app and ARQ worker
python sandbox_fastapi/start_dev.py
```

This development script will start:
1. ARQ worker in the background for task processing
2. FastAPI application with live reload on port 8080

Once running, you can access:
- **FastAPI application**: http://localhost:8080

## Code quality tools

Chanx uses several tools to ensure code quality. You should run these tools before submitting a pull request.

### Pre-commit hooks

We use pre-commit hooks to automatically check and format your code on commit. Install them with:

```bash
uv tool install pre-commit
pre-commit install
```

### Linting and formatting

For manual linting and formatting:

```bash
# Run linting checks
bash scripts/lint.sh

# Fix linting issues automatically
bash scripts/lint.sh --fix
```

This runs:
- [Ruff](https://github.com/astral-sh/ruff) for fast Python linting
- [Black](https://github.com/psf/black) for code formatting
- [toml-sort](https://github.com/pappasam/toml-sort) for TOML file formatting

### Type checking

We use multiple type checking tools for maximum safety:

```bash
# Run mypy on the chanx package
bash scripts/mypy.sh

# Run mypy on the sandbox_django
bash scripts/mypy.sh --django

# Run mypy on the sandbox_fastapi
bash scripts/mypy.sh --fastapi

# Run mypy on the tests
bash scripts/mypy.sh --tests

# Run pyright
pyright
```

The project uses strict type checking settings to ensure high code quality.

### Docstring coverage

We aim for high docstring coverage. Check your docstring coverage with:

```bash
# Run interrogate to check docstring coverage
interrogate -vv chanx
```

The project requires at least 80% docstring coverage as configured in the project settings.

## Testing

### Running tests

```bash
# Run all tests
bash scripts/test_all.sh

# Run tests with coverage report
bash scripts/test_all.sh --cov
```

The test script runs tests for:
- `sandbox_django` - Django integration tests
- `sandbox_fastapi` - FastAPI integration tests
- `tests/ext/channels` - Django Channels extension tests
- `tests/ext/fast_channels` - FastAPI and other framework extension tests
- `tests/core` - Core functionality tests

### Writing tests

When adding new features, please include appropriate tests in the `tests/` or relevant sandbox directories. Tests should:

- Verify the expected behavior of your feature
- Include both success and failure cases
- Use the fixtures and utilities provided by the testing framework

## Validating your changes before submission

Before creating a pull request, please ensure your code meets the project's standards:

### 1. Run the test suite

```bash
bash scripts/test_all.sh --cov
```

### 2. Run type checkers

```bash
bash scripts/mypy.sh
bash scripts/mypy.sh --django
bash scripts/mypy.sh --fastapi
bash scripts/mypy.sh --tests
pyright
```

### 3. Lint and format your code

```bash
bash scripts/lint.sh --fix
```

### 4. Check docstring coverage

```bash
interrogate -vv chanx
```

### 5. Run the complete validation suite with tox

```bash
tox
```

## Commit guidelines

For committing code, use the [Commitizen](https://commitizen-tools.github.io/commitizen/) tool to follow
commit best practices:

```bash
# Install commitizen if not already installed
uv tool install commitizen

# Create a conventional commit
cz commit
```

This ensures that all commits follow the [Conventional Commits](https://www.conventionalcommits.org/) format.

## Creating a Pull Request

When creating a pull request:

1. Make sure all tests pass and code quality checks succeed
2. Update the documentation if needed
3. Add a clear description of your changes
4. Reference any related issues

## Development best practices

- **Keep changes focused**: Each PR should address a single concern
- **Write descriptive docstrings**: All public API functions should be well-documented
- **Add type annotations**: All code should be properly typed
- **Follow Django conventions**: Use Django best practices for models and views
- **Test thoroughly**: Include tests for all new functionality

Thank you for contributing to chanx!
