# ARS-RULE-00004: ai-ressources/architecture/database-migrations.md:15 #1-migration-types
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
