# ARS-RULE-00302: ai-ressources/code-conventions/database.md:136 #25-idempotent-operations
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
