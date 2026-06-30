# ARS-RULE-00265: ai-ressources/code-conventions/database.md:40 #7-multi-tenant-data-isolation
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
