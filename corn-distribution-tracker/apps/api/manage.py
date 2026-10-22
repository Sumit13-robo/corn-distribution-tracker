#!/usr/bin/env python
"""Django management entrypoint for the Corn Distribution Tracker API."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment failure
        raise ImportError(
            "Django is not installed. Activate the project virtualenv and install "
            "apps/api/requirements.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
