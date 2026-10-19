"""Export the OpenAPI document without running a server.

Usage: `python -m taskmanager.presentation.openapi > openapi.json`, or `make types`.
The frontend generates its API types from this file, and CI fails if they drift (CR-011).
"""

import json
import sys

from taskmanager.presentation.app import create_app


def main() -> None:
    json.dump(create_app().openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
