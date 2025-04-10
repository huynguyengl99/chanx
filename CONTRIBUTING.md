# Contributing to chanx

Contributions are welcome! Here are some pointers to help you install the library for development and validate your changes before submitting a pull request.

## Prerequisites

Before starting development, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python package management

## Install the library for development

Create your own virtual environment and activate it:

```bash
uv venv
source .venv/bin/activate
```

Then use uv to install all dev packages:
```bash
uv sync
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
- Run `docker-compose up` to create necessary databases/services

## Working with the sandbox project

### Setting up and running the sandbox

```bash
# Apply database migrations
python sandbox/manage.py migrate

# Create a superuser for accessing the admin interface
python sandbox/manage.py createsuperuser

# Run Django development server
python sandbox/manage.py runserver
```

Once the server is running, you can:
- Access the admin interface at http://127.0.0.1:8000/admin/
- Test API endpoints
- Verify your package functionality in a real Django environment

### Development commands

```bash
# Create migrations for your changes
python sandbox/manage.py makemigrations
```

## Validating your changes before submission

Before creating a pull request, please ensure your code meets the project's standards.

### 1. Run the test suite

Make sure the existing tests are still passing (and consider adding new tests as well!):

```bash
pytest --cov-report term-missing --cov=chanx sandbox
```

### 2. Lint and format your code

```bash
bash scripts/lint.sh [--fix]
```

### 3. Use proper commit practices

For committing code, use the [Commitizen](https://commitizen-tools.github.io/commitizen/) tool to follow
commit best practices:

```bash
cz commit
```

These validation steps are also run automatically in the CI when you open the pull request.
