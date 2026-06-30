/* ARS-RULE-01202: ai-ressources/code-conventions/tanstack.md:45 #configuration */
const fs = require("fs");
export const value = fs.readFileSync("x");
