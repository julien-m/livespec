# ARS-RULE-00292: ai-ressources/code-conventions/database.md:117 #20-batch-large-deletes
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
