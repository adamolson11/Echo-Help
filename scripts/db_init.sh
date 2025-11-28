#!/usr/bin/env bash
set -e

PYTHONPATH=$(pwd) python -m backend.app.db_init
