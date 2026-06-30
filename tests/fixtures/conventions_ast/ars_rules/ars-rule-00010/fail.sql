# ARS-RULE-00010: ai-ressources/architecture/database-migrations.md:31 #numbering-strategies
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
