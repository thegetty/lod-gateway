# The following environment variables need to be set before things will work and build, these needs to be done
# in the local shell, replacing the values that are placeholders on the right with the actual values needed.
# For the VAULT_* values you need to know what these are, talk to an admin to get these.
# They are removed intentionally to alleviate them from getting checked in and are passed at build time for NPM and 
# at run-time for vault using envconsul

##### export the var's necessary to run the application locally:
#export VAULT_ADDR="replacewithVaultaddress"
#export VAULT_TOKEN="replaceWithGeneratedAppRoleToken" 
#export VAULT_ENV="replaceWithEnvironment"
#export VAULT_APP_NAME="replaceWithAppName"

# Build the museum-collections-data-to-linked-art
# Assuming you checked out to a location that resides in the same directory as provenanceindex
cd ../
docker build -t mart-web-service -f Dockerfile.webservice .
docker build -t mart-transformer -f Dockerfile.transformer .

# Create the docker network for these to communicate and have the short docker names resolve 
# This is required before the docker run commands and scripts will function
docker network create mart
