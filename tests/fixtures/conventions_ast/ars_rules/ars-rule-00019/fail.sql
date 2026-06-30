# ARS-RULE-00019: ai-ressources/architecture/database-migrations.md:73 #3-zero-downtime-migrations-expand-contract
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
