#!/bin/bash

RETRIES=50;

echo "Checking if PostgreSQL is running...";

until PGPASSWORD=${POSTGRES_PASSWORD} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "select 1" > /dev/null 2>&1 || (( ${RETRIES} == 0 )); do
	echo "Waiting for PostgreSQL server; $((RETRIES)) remaining attempts...";
	
	RETRIES=$((RETRIES-=1));
	
	if (( $RETRIES == 0 )); then
		exit 9;
	fi
	
	sleep 1;
done