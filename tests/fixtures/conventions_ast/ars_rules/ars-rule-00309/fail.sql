# ARS-RULE-00309: ai-ressources/code-conventions/database.md:156 #31-input-normalization-validation-parameter-safety
CREATE TABLE users(id int);
UPDATE users SET id = id;
SELECT * FROM users;
