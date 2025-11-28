#!/usr/bin/env bash

# Function to show usage
show_usage() {
    echo "Usage: $0 [--cov]"
    echo "  --cov    Run tests with coverage reporting"
    echo "  (no args) Run tests without coverage"
    exit 1
}

# Check arguments
RUN_COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --cov)
            RUN_COVERAGE=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Run tests based on coverage flag
if [ "$RUN_COVERAGE" = true ]; then
    echo "Running tests with coverage..."

    pytest --cov=chanx --cov-report= sandbox_django

    pytest --cov=chanx --cov-report= --cov-append sandbox_fastapi

    pytest --cov=chanx --cov-report= --cov-append tests/ext/channels

    pytest --cov=chanx --cov-report= --cov-append tests/client_generation/

    pytest --cov=chanx --cov-append --cov-report=xml --cov-report=term-missing tests/core

else
    echo "Running tests without coverage..."

    pytest sandbox_django

    pytest sandbox_fastapi

    pytest tests/ext/channels

    pytest tests/client_generation/

    pytest tests/core
fi
