docker run --network=lod-gateway --name=lod-gateway-transformer-service --rm -p 5200:5200 -d \
-e VAULT_ADDR="${VAULT_ADDR}" \
-e VAULT_TOKEN="${VAULT_TOKEN}" \
-e VAULT_ENV="${VAULT_ENV}" \
-e VAULT_APP_NAME="${VAULT_APP_NAME}" \
lod-gateway-transformer-service:latest
