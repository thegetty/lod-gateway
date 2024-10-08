#!/bin/bash

echo "$(date -Iseconds) Beginning application script"

if [ "$DB_UPGRADE_ON_START" == "true" ]; then
    echo "Attempting DB upgrade -"
    flask db upgrade 
fi

# Worker type
WORKER_CLASS="${WORKER_CLASS:-sync}"

# Number of threads
THREADS="${WEB_THREADS:-1}"

# Workers rule of thumb -> 2 to 4 X (number of cores available)
WORKERS="${WEB_WORKERS:-8}"
WORKER_CONNECTIONS="${WORKER_CONNECTIONS:-100}"

TIMEOUT="${WEB_TIMEOUT:-600}"
KEEPALIVE="${WEB_KEEPALIVE:-75}"

FLASK_RUN_PORT="${FLASK_RUN_PORT:-5100}"

# sync/threads? or green threads?
if [[ "$WORKER_CLASS" != "gevent" ]]; then
	echo "Running with either sync/gthreads - $WORKERS workers, $THREADS threads" && \
    gunicorn --bind 0.0.0.0:${FLASK_RUN_PORT} \
         --threads ${THREADS} \
         --workers ${WORKERS} \
         --worker-class ${WORKER_CLASS} \
         --timeout ${TIMEOUT} \
         --keep-alive ${KEEPALIVE} \
         --access-logfile '-' \
         --error-logfile '-' \
         --worker-tmp-dir /dev/shm \
         wsgi:app
	$@
else
	echo "Running with gevents - $WORKERS workers, $WORKER_CONNECTIONS connections" && \
    gunicorn --bind 0.0.0.0:${FLASK_RUN_PORT} \
         --worker-connections ${WORKER_CONNECTIONS} \
         --workers ${WORKERS} \
         --worker-class ${WORKER_CLASS} \
         --timeout ${TIMEOUT} \
         --keep-alive ${KEEPALIVE} \
         --access-logfile '-' \
         --error-logfile '-' \
         --worker-tmp-dir /dev/shm \
         wsgi:app
	$@
fi