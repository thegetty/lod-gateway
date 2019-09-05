# The following environment variables need to be set before things will work and build, these needs to be done
# in the local shell, replacing the values that are placeholders on the right with the actual values needed.
# For the VAULT_* values you need to know what these are, to get these you can look in the vault path for the
# relative environment you are working with.  If you are using the dev path in vault then the VAULT_TOKEN can
# be the token available to you after you login to vault.  The token in staging is built by an admin and is
# appRole specific (in other words it has a ttl of 24h but renews at half that time if the process is running) and
# is limited to read-only for the path to the specific application. 
# These env var's are removed intentionally to alleviate them from getting checked in and are passed
# at run-time for vault using envconsul

# export the var's necessary to run the application locally, you should be able to get these in the VAULT path
# relative to the project.  If they don't exist ask devOps to help you get them put in vault so that you can
# reference them.

#export VAULT_ADDR="replacewithVaultaddress"
#export VAULT_TOKEN="replaceWithGeneratedAppRoleToken" 
#export VAULT_ENV="replaceWithEnvironment"
#export VAULT_APP_NAME="replaceWithAppName"

# Build the museum-collections-data-to-linked-art
cd ../
docker build -t mart-db-service -f Dockerfile.db-service .
docker build -t mart-web-service -f Dockerfile.web-service .
docker build -t mart-transformer-service -f Dockerfile.transformer-service .
