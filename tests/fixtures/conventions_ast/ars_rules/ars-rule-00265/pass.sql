# ARS-RULE-00265: ai-ressources/code-conventions/database.md:40 #7-multi-tenant-data-isolation
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
