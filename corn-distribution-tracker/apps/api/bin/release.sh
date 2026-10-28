#!/bin/sh
set -eu

# Railway runs this once before the new container receives traffic.
python manage.py migrate --noinput
