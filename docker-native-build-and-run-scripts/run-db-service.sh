docker run --network=mart --name=mart-db-service --rm -p 5432:5432 \
-e VAULT_ADDR=${VAULT_ADDR} \
-e VAULT_ENV=${VAULT_ENV} \
-e VAULT_APP_NAME=${VAULT_APP_NAME} \
-e VAULT_TOKEN=${VAULT_TOKEN} \
--mount 'type=volume,source=data_postgres,target=/var/lib/postgresql/data' \
mart-db-service:latest
