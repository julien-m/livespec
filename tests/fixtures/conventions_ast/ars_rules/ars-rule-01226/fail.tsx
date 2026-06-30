/* ARS-RULE-01226: ai-ressources/code-conventions/tanstack.md:112 #anti-patterns */
const fs = require("fs");
export const value = fs.readFileSync("x");
