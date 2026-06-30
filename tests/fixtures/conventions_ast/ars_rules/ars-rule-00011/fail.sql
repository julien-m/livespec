# ARS-RULE-00011: ai-ressources/architecture/database-migrations.md:55 #migration-ledger
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
