docker run --network=mart --name=mart-db-service --rm -p 5432:5432 -d \
-e POSTGRES_HOST=${MART_POSTGRES_HOST} \
-e POSTGRES_USER=${MART_POSTGRES_USER} \
-e POSTGRES_PASSWORD=${MART_POSTGRES_PASSWORD} \
-e POSTGRES_DB=${MART_POSTGRES_DB} \
-e POSTGRES_PORT=${MART_POSTGRES_PORT} \
-e PGDATA=${MART_PGDATA} \
-e TZ=${MART_TIMEZONE} \
--mount 'type=volume,source=data_postgres,target=/var/lib/postgresql/data' \
mart-db-service:latest
