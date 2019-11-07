docker run --network=lod-gateway --name=lod-gateway-db-service --rm -p 5432:5432 -d \
-e VAULT_ADDR=${VAULT_ADDR} \
-e VAULT_ENV=${VAULT_ENV} \
-e VAULT_APP_NAME=${VAULT_APP_NAME} \
-e VAULT_TOKEN=${VAULT_TOKEN} \
--mount 'type=volume,source=data_postgres,target=/var/lib/postgresql/data' \
lod-gateway-db-service:latest
