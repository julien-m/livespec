# ARS-RULE-00389: ai-ressources/code-conventions/drizzle.md:111 #anti-patterns
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
