#!/usr/bin/env bash
# Executa testes com src/ no PYTHONPATH (sem pip install -e .)
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
exec python3 -m unittest discover -s tests -v "$@"
