# ARS-RULE-00315: ai-ressources/code-conventions/database.md:168 #parameterized-queries-mandatory
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
