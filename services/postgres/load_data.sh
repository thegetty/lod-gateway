#!/bin/bash

if [ -f /tmp/sample_data.sql ]; then
	if [ -s /tmp/sample_data.sql ]; then
		PGPASSWORD=${POSTGRES_PASSWORD} psql -U ${POSTGRES_USER} -f /tmp/sample_data.sql ${POSTGRES_DB};
	else
		echo "/tmp/sample_data.sql is empty, so it will not be processed!";
	fi
else
	echo "/tmp/sample_data.sql does not exist, so it can not be processed!";
fi