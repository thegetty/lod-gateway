# See https://hub.docker.com/_/postgres
FROM postgres:9.6.11

MAINTAINER Daniel Sissman <dsissman@getty.edu>
MAINTAINER Viktor Grabarchuk <vgrabarchuk@getty.edu>

RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8

# RUN useradd -m -s /bin/bash mart
# RUN chown -R mart /var/lib/postgresql/data
# RUN chmod 777 -R /var/lib/postgresql/data

# USER mart
# WORKDIR /home/mart

# RUN touch /var/lib/postgresql/data/hello

# RUN mkdir /var/lib/postgresql/data/mart
# ENV PGDATA /var/lib/postgresql/data/mart

# RUN initdb --auth=trust --pgdata=/var/lib/postgresql/data/mart
# EXPOSE 5432

# COPY ./services/postgres/<script>.sh /docker-entrypoint-initdb.d/##-<script>.sh
# COPY ./services/postgres/<script>.sql /docker-entrypoint-initdb.d/##-<script>.sql

COPY ./services/postgres/scripts/01-create-hstore.sql /docker-entrypoint-initdb.d/01-create-hstore.sql
COPY ./services/postgres/scripts/02-create-schema.sql /docker-entrypoint-initdb.d/02-create-schema.sql
# COPY ./services/postgres/scripts/03-sample-data.sql /docker-entrypoint-initdb.d/03-sample-data.sql

COPY ./services/postgres/is_postgres_ready.sh /usr/local/bin/is_postgres_ready.sh
RUN chmod +x /usr/local/bin/is_postgres_ready.sh