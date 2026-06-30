# ARS-RULE-00388: ai-ressources/code-conventions/drizzle.md:110 #anti-patterns
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
