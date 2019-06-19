DROP TABLE IF EXISTS activities;
CREATE TABLE activities (
	id BIGSERIAL PRIMARY KEY,
	datetime_started DATE,
	datetime_ended DATE,
	datetime_published DATE,
	activity VARCHAR NOT NULL,
	entity VARCHAR NOT NULL,
	entity_id INT8 NOT NULL
);

DROP TABLE IF EXISTS records;
CREATE TABLE records (
	id BIGSERIAL PRIMARY KEY,
	datetime_created DATE,
	datetime_updated DATE,
	datetime_published DATE,
	entity VARCHAR NOT NULL,
	uuid UUID NOT NULL,
	data JSON,
	attributes HSTORE
);