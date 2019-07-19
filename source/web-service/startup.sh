#!/bin/bash

# determine the path to this script, regardless of where it is run from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

echo "startup.sh path: ${DIR}";

# run the process...

# if running our script directly on the command line (detected here by ${DIR} not being "/")...
if [ "${DIR}" != "/" ]; then
	# import our environment variables...
	ENV="$( cd "$( dirname "${DIR}/../../.env" )" && pwd )/.env";
	
	# see https://stackoverflow.com/questions/19331497/set-environment-variables-from-file-of-key-pair-values
	# see https://unix.stackexchange.com/questions/26235/how-can-i-cat-a-file-and-remove-commented-lines
	/usr/bin/env $(grep -v '^#' "${ENV}" | xargs) FLASK_ENV=MART_FLASK_ENV FLASK_DEBUG=MART_FLASK_DEBUG FLASK_APP=MART_FLASK_APP flask run --host=0.0.0.0 --port=5100 $@;
else # or when running in Docker...
	echo "startup.sh: running within docker"
	
	# ...our environment variables will be available through docker-compose.yml or from Hashicorp Vault in production
	flask run --host=0.0.0.0 --port=5100 $@
fi