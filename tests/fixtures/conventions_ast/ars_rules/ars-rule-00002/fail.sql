# ARS-RULE-00002: ai-ressources/architecture/database-migrations.md:13 #1-migration-types
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
