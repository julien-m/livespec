# ARS-RULE-00300: ai-ressources/code-conventions/database.md:132 #24-concurrency
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
