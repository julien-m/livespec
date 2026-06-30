# ARS-RULE-00006: ai-ressources/architecture/database-migrations.md:18 #1-migration-types
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
