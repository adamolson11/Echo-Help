#!/usr/bin/env bash
set -e

PYTHONPATH=$(pwd) python -m backend.app.db_init

if [[ "${ECHOHELP_SEED_DEMO:-}" == "1" || "${SEED_DEMO:-}" == "1" ]]; then
	PYTHONPATH=$(pwd) python scripts/seed_demo_org.py
fi
