# ARS-RULE-00321: ai-ressources/code-conventions/database.md:175 #non-parameterizable-elements
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
