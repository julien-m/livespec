# ARS-RULE-00299: ai-ressources/code-conventions/database.md:131 #24-concurrency
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
