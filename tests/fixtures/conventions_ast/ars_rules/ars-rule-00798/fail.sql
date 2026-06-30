# ARS-RULE-00798: ai-ressources/code-conventions/prisma.md:106 #transactions
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
