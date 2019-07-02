#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

echo "startup.sh path ${DIR}";

# run the process...

# if running our script directly on the command line (detected here by ${DIR} not being "/")...
if [ "${DIR}" != "/" ]; then
	# import our environment variables from our .evn file...
	ENV="$( cd "$( dirname "${DIR}/../../.env" )" && pwd )/.env";
	
	# see https://stackoverflow.com/questions/19331497/set-environment-variables-from-file-of-key-pair-values
	# see https://unix.stackexchange.com/questions/26235/how-can-i-cat-a-file-and-remove-commented-lines
	/usr/bin/env $(grep -v '^#' "${ENV}" | xargs) python3 "${DIR}/startup.py" $@;
else # or when running in Docker...
	# ...our environment variables will be available through docker-compose.yml or from Hashicorp Vault in production
	python3 "${DIR}/startup.py" $@;
fi
