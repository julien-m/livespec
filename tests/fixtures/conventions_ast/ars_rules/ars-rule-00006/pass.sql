# ARS-RULE-00006: ai-ressources/architecture/database-migrations.md:18 #1-migration-types
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
