"""Pytest conftest: scrubs hermes-agent contamination from sys.path.

The cron job's Python invocation inherits PYTHONPATH from the Hermes
environment, which points to hermes-agent's venv. That venv has a
broken rpds-py install. We need the project venv to take priority
for all test imports.

This file runs before any test module is collected, so it scrubs
sys.path before pytest (or any test module) imports anything.
"""
import sys

# Strip hermes paths already prepended to sys.path
sys.path[:] = [p for p in sys.path if "hermes" not in p.lower()]

# Also scrub env vars
import os
for env_var in ("PYTHONPATH", "PYTHONHOME"):
    if env_var in os.environ:
        del os.environ[env_var]
for env_var in list(os.environ.keys()):
    if "hermes" in os.environ[env_var].lower():
        del os.environ[env_var]
