#!/bin/bash

flask db upgrade 

THREADS="${WEB_THREADS:-1}"

# Workers rule of thumb -> 2 to 4 X (number of cores available)
WORKERS="${WEB_WORKERS:-3}"

FLASK_RUN_PORT="${FLASK_RUN_PORT:-5100}"

gunicorn --bind 0.0.0.0:${FLASK_RUN_PORT} \
         --threads ${THREADS} \
         --workers ${WORKERS} \
         --access-logfile '-' \
         --error-logfile '-' \
         wsgi:app
	$@