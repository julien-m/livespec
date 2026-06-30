# ARS-RULE-00011: ai-ressources/architecture/database-migrations.md:55 #migration-ledger
CREATE TABLE users(id int);
CREATE INDEX users_id_idx ON users(id);
