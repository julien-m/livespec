# ARS-RULE-00004: ai-ressources/architecture/database-migrations.md:15 #1-migration-types
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
