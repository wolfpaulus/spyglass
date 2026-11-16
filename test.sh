#!/bin/sh
set -eu

cd "$(dirname "$0")"
pytest
genbadge coverage -i coverage.xml -o coverage.svg -l
