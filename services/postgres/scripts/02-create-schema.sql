/* define the activities table */
DROP TABLE IF EXISTS activities;
CREATE TABLE activities (
	id BIGSERIAL PRIMARY KEY,
	uuid UUID NOT NULL,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	datetime_started TIMESTAMPTZ,
	datetime_ended TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	namespace VARCHAR NOT NULL,
	entity VARCHAR NOT NULL,
	record_id INT8 NOT NULL,
	event VARCHAR NOT NULL
);

DROP INDEX IF EXISTS namespace_index;
CREATE INDEX namespace_index ON activities (namespace);

DROP INDEX IF EXISTS entity_index;
CREATE INDEX entity_index ON activities (entity);

DROP INDEX IF EXISTS record_id_index;
CREATE INDEX record_id_index ON activities (record_id);

DROP INDEX IF EXISTS event_index;
CREATE INDEX event_index ON activities (event);

/* define the records table */
DROP TABLE IF EXISTS records;
CREATE TABLE records (
	id BIGSERIAL PRIMARY KEY,
	uuid UUID NOT NULL,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	namespace VARCHAR NOT NULL,
	entity VARCHAR NOT NULL,
	data JSON,
	counter INT8 NOT NULL DEFAULT 0,
	attributes HSTORE
);

DROP INDEX IF EXISTS uuid_index;
CREATE INDEX uuid_index ON records (uuid);

DROP INDEX IF EXISTS namespace_index;
CREATE INDEX namespace_index ON records (namespace);

DROP INDEX IF EXISTS entity_index;
CREATE INDEX entity_index ON records (entity);

DROP INDEX IF EXISTS counter_index;
CREATE INDEX counter_index ON records (counter);


/* define the streams table */
DROP TABLE IF EXISTS streams;
CREATE TABLE streams (
	id BIGSERIAL PRIMARY KEY,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	namespace VARCHAR NOT NULL,
	base_url VARCHAR NOT NULL,
	last_id VARCHAR NULL
);

DROP INDEX IF EXISTS namespace_index;
CREATE UNIQUE INDEX namespace_index ON streams (namespace);

DROP INDEX IF EXISTS base_url_index;
CREATE UNIQUE INDEX base_url_index ON streams (base_url);