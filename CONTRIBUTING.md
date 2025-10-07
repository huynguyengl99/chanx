# Contributing to chanx

Thank you for your interest in contributing to chanx! This guide will help you set up the development environment and
understand the tools and processes used in this project.

## Prerequisites

Before starting development, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python package management
- Python 3.10+ (project supports 3.10, 3.11, 3.12, and 3.13)

## Install the library for development

### Setting up your environment

Create your own virtual environment and activate it:

```bash
uv venv
source .venv/bin/activate
```

Then use uv to install all dev packages:
```bash
uv sync
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
tox -e py310-django5

# Run only the linting checks
tox -e lint

# Run test coverage
tox -e coverage
```

## Understanding the project structure

The project uses a `sandbox` directory which serves two main purposes:

1. **Testing Environment**: Write and run tests for the package
   - Contains test applications and configurations
   - Used with pytest to validate package functionality

2. **Development Playground**: Run as a Django application to test features
   - Run Django commands like `makemigrations` and `migrate`
   - Interact with API endpoints for manual testing
   - Test UI components and integrations

## Prepare the environment

Before working with the sandbox or running tests, ensure:
- Docker is running
- Run `docker compose up` to create necessary databases/services

## Working with the sandbox project

### Setting up and running the sandbox

```bash
# Apply database migrations
python sandbox_django/manage.py migrate

# Create a superuser for accessing the admin interface
python sandbox_django/manage.py createsuperuser

# Run Django development server
python sandbox_django/manage.py runserver
```

Once the server is running, you can:
- Access the admin interface at http://127.0.0.1:8000/admin/
- Test API endpoints
- Verify your package functionality in a real Django environment

### Development commands

```bash
# Create migrations for your changes
python sandbox_django/manage.py makemigrations
```

## Code quality tools

Chanx uses several tools to ensure code quality. You should run these tools before submitting a pull request.

### Pre-commit hooks

We use pre-commit hooks to automatically check and format your code on commit. Install them with:

```bash
pip install pre-commit
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
bash scripts/mypy.sh --sandbox_django

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
pytest sandbox_django

# Run tests with coverage report
pytest --cov-report term-missing --cov=chanx sandbox_django
```

### Writing tests

When adding new features, please include appropriate tests in the `sandbox` directory. Tests should:

- Verify the expected behavior of your feature
- Include both success and failure cases
- Use the fixtures and utilities provided by the testing framework

## Validating your changes before submission

Before creating a pull request, please ensure your code meets the project's standards:

### 1. Run the test suite

```bash
pytest --cov-report term-missing --cov=chanx sandbox_django
```

### 2. Run type checkers

```bash
bash scripts/mypy.sh
bash scripts/mypy.sh --sandbox_django
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
