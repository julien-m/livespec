# ARS-RULE-00047: ai-ressources/architecture/database-migrations.md:179 #forward-only-vs-reversible
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
