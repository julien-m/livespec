# ARS-RULE-00062: ai-ressources/architecture/database-migrations.md:251 #7-anti-patterns
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
