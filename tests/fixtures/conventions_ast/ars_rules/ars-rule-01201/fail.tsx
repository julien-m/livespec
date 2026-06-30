/* ARS-RULE-01201: ai-ressources/code-conventions/tanstack.md:44 #configuration */
const fs = require("fs");
export const value = fs.readFileSync("x");
