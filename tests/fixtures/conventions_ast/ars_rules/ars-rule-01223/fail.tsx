/* ARS-RULE-01223: ai-ressources/code-conventions/tanstack.md:93 #configuration */
const fs = require("fs");
export const value = fs.readFileSync("x");
