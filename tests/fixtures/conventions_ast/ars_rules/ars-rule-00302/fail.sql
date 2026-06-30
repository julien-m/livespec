# ARS-RULE-00302: ai-ressources/code-conventions/database.md:136 #25-idempotent-operations
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
