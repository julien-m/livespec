# ARS-RULE-00319: ai-ressources/code-conventions/database.md:173 #non-parameterizable-elements
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
