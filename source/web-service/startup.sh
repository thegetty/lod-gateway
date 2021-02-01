#!/bin/bash

flask db upgrade 

uwsgi \
	--ini ./uwsgi.ini \
	--http "0.0.0.0:${FLASK_RUN_PORT}" \
	$@