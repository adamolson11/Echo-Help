#!/usr/bin/env bash
set -e

rm -f echohelp.db
PYTHONPATH=$(pwd) python -m backend.app.db_init
