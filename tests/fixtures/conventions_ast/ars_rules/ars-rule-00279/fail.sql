# ARS-RULE-00279: ai-ressources/code-conventions/database.md:86 #13-batch-operations
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
