#!/bin/bash

# determine the path to this script, regardless of where it is run from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

echo "startup.sh path: ${DIR}";

# run the process via uWSGI...
uwsgi \
	--http "0.0.0.0:${WEB_SERVICE_PORT}" \
	--manage-script-name \
	--wsgi-file="${DIR}/startup.py" \
	--callable "app" \
	--master \
	--processes=${UWSGI_PROCESSES} \
	--threads=${UWSGI_THREADS} \
	--thunder-lock \
	$@