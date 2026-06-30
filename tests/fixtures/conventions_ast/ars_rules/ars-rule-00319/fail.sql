# ARS-RULE-00319: ai-ressources/code-conventions/database.md:173 #non-parameterizable-elements
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
