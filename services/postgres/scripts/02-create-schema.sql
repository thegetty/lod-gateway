DROP TABLE IF EXISTS activities;
CREATE TABLE activities (
	id BIGSERIAL PRIMARY KEY,
	datetime_started TIMESTAMPTZ,
	datetime_ended TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	activity VARCHAR NOT NULL,
	entity VARCHAR NOT NULL,
	entity_id INT8 NOT NULL
);

DROP TABLE IF EXISTS records;
CREATE TABLE records (
	id BIGSERIAL PRIMARY KEY,
	datetime_created TIMESTAMPTZ,
	datetime_updated TIMESTAMPTZ,
	datetime_published TIMESTAMPTZ,
	entity VARCHAR NOT NULL,
	uuid UUID NOT NULL,
	data JSON,
	attributes HSTORE,
	counter INT8 NOT NULL DEFAULT 0
);