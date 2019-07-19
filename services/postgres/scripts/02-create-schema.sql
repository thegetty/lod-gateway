DROP TABLE IF EXISTS activities;
CREATE TABLE activities (
	id BIGSERIAL PRIMARY KEY,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	datetime_started TIMESTAMPTZ,
	datetime_ended TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	event VARCHAR NOT NULL,
	entity_id INT8 NOT NULL,
	record_id INT8 NOT NULL
);

DROP INDEX IF EXISTS entity_id_index;
CREATE UNIQUE INDEX entity_id_index ON activities (entity_id);

DROP INDEX IF EXISTS record_id_index;
CREATE UNIQUE INDEX record_id_index ON activities (record_id);

DROP TABLE IF EXISTS entities;
CREATE TABLE entities (
	id BIGSERIAL PRIMARY KEY,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	entity VARCHAR NOT NULL
);

DROP INDEX IF EXISTS entity_index;
CREATE UNIQUE INDEX entity_index ON entities (entity);

DROP TABLE IF EXISTS records;
CREATE TABLE records (
	id BIGSERIAL PRIMARY KEY,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	namespace VARCHAR NOT NULL,
	entity VARCHAR NOT NULL,
	uuid UUID NOT NULL,
	data JSON,
	attributes HSTORE,
	counter INT8 NOT NULL DEFAULT 0
);

DROP INDEX IF EXISTS namespace_index;
CREATE UNIQUE INDEX namespace_index ON records (namespace);

DROP INDEX IF EXISTS entity_index;
CREATE UNIQUE INDEX entity_index ON records (entity);

DROP INDEX IF EXISTS uuid_index;
CREATE UNIQUE INDEX uuid_index ON records (uuid);