# ARS-RULE-00305: ai-ressources/code-conventions/database.md:143 #27-safe-schema-evolution
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
