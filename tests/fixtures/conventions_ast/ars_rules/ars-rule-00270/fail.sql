# ARS-RULE-00270: ai-ressources/code-conventions/database.md:62 #9-query-typing-schema-safety
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
