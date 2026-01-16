#!/bin/bash
set -e

echo "Running Ruff linting..."
ruff check .

echo "Running Ruff formatting check..."
ruff format --check .

echo "Running Mypy type checking..."
mypy .
