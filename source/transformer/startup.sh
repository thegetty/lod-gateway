#!/bin/bash

# determine the path to this script, regardless of where it is run from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

echo "startup.sh path: ${DIR}";

# run the process...

# if running our script directly on the command line (detected here by ${DIR} not being "/")...
# if [ "${DIR}" != "/" ]; then
# 	# import our environment variables...
# 	ENV="$( cd "$( dirname "${DIR}/../../.env" )" && pwd )/.env";
# 	
# 	# see https://stackoverflow.com/questions/19331497/set-environment-variables-from-file-of-key-pair-values
# 	# see https://unix.stackexchange.com/questions/26235/how-can-i-cat-a-file-and-remove-commented-lines
# 	/usr/bin/env $(grep -v '^#' "${ENV}" | xargs) python3 "${DIR}/startup.py" $@;
# else # or when running in Docker...
# 	# ...our environment variables will be available through docker-compose.yml or from Hashicorp Vault in production
# 	python3 "${DIR}/startup.py" $@;
# fi

# Test for CRLF - LF fix

export MART_NEPTUNE_ENABLED="NO"

python3 "${DIR}/startup.py" --manager records --namespace museum/collection --entity Gallery --id /usr/local/mart/data/ids/Gallery_IDs.txt;
python3 "${DIR}/startup.py" --manager records --namespace museum/collection --entity Exhibition --id /usr/local/mart/data/ids/Exhibition_IDs.txt;
python3 "${DIR}/startup.py" --manager records --namespace museum/collection --entity Artifact --id /usr/local/mart/data/ids/GettyGuide_Center_Object_IDs.txt;
python3 "${DIR}/startup.py" --manager records --namespace museum/collection --entity Artifact --id /usr/local/mart/data/ids/GettyGuide_Villa_Object_IDs.txt;
python3 "${DIR}/startup.py" --direction first $@;