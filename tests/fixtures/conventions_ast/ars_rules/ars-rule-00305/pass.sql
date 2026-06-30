# ARS-RULE-00305: ai-ressources/code-conventions/database.md:143 #27-safe-schema-evolution
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
