#!/bin/bash

# determine the path to this script, regardless of where it is run from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

echo "startup.sh path: ${DIR}";

# run the process
if [ "${DIR}" != "/" ]; then
	# if running our script directly on the command line, import our environment variables
	ENV="$( cd "$( dirname "${DIR}/../../.env" )" && pwd )/.env";
	
	# see https://stackoverflow.com/questions/19331497/set-environment-variables-from-file-of-key-pair-values
	# see https://unix.stackexchange.com/questions/26235/how-can-i-cat-a-file-and-remove-commented-lines
	/usr/bin/env $(grep -v '^#' "${ENV}" | xargs) python3 "${DIR}/startup.py" $@;
else
	# when running in Docker, our environment variables will be available through our docker-compose.yml
	# or through the integrations with Hashicorp Vault in production
	python3 "${DIR}/startup.py" $@;
fi
