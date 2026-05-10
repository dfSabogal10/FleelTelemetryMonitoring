-- Created on first Postgres volume initialization only.
-- Separate database for pytest so tests never touch the dev `fleet` database.
CREATE DATABASE fleet_test;
