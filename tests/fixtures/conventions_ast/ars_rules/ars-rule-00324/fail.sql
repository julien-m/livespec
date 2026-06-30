# ARS-RULE-00324: ai-ressources/code-conventions/database.md:179 #pre-query-input-validation
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
