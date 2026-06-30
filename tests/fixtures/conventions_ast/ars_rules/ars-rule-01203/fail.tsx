/* ARS-RULE-01203: ai-ressources/code-conventions/tanstack.md:46 #configuration */
const fs = require("fs");
export const value = fs.readFileSync("x");
