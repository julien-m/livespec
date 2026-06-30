# ARS-RULE-00018: ai-ressources/architecture/database-migrations.md:67 #tooling
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
