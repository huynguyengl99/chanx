#!/usr/bin/env bash

if [ "$1" == "--fix" ]; then
  ruff check . --fix && black ./chanx && toml-sort ./*.toml
else
  ruff check . && black ./chanx --check && toml-sort ./*.toml --check
fi
