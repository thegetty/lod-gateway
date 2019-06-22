#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

# run the process
echo "startup.sh path ${DIR}";

if [ "${DIR}" != "/" ]; then
	ENV="$( cd "$( dirname "${DIR}/../../.env" )" && pwd )/.env";
	
	/usr/bin/env $(grep -v '^#' ${ENV} | xargs) python3 ${DIR}/startup.py $@
else
	python3 ${DIR}/startup.py $@
fi
