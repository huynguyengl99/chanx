#!/usr/bin/env bash

if [ "$1" == "--fix" ]; then
  ruff check . --fix && black ./ && toml-sort ./*.toml
else
  ruff check . && black ./ --check && toml-sort ./*.toml --check
fi
