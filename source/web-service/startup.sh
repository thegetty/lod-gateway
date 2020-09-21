#!/bin/bash

flask db upgrade 

uwsgi \
	--http "0.0.0.0:${FLASK_RUN_PORT}" \
	--manage-script-name \
	--wsgi-file "./wsgi.py" \
	--callable "app" \
	--master \
	--processes ${UWSGI_PROCESSES} \
	--threads ${UWSGI_THREADS} \
	--thunder-lock \
	$@