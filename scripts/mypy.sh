#!/usr/bin/env bash

set -e

rm -rf .mypy_cache/

if [ "$1" == "--django" ]; then
    export PYTHONPATH="sandbox_django"
    export MYPYPATH='.'
    export DJANGO_SETTINGS_MODULE=config.settings.dev
    mypy sandbox_django
elif [ "$1" == "--fastapi" ]; then
    export PYTHONPATH="sandbox_fastapi"
    export MYPYPATH='.'
    export DJANGO_SETTINGS_MODULE=chanx.ext.channels.settings
    mypy sandbox_fastapi
elif [ "$1" == "--tests" ]; then
    export PYTHONPATH="tests"
    export MYPYPATH='.'
    export DJANGO_SETTINGS_MODULE=chanx.ext.channels.settings
    mypy tests
else
    export DJANGO_SETTINGS_MODULE=chanx.ext.channels.settings
    mypy chanx
fi
