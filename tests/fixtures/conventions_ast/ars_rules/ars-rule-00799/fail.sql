# ARS-RULE-00799: ai-ressources/code-conventions/prisma.md:107 #transactions
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
