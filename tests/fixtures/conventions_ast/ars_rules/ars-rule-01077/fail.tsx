/* ARS-RULE-01077: ai-ressources/code-conventions/shadcn.md:83 #anti-patterns */
const fs = require("fs");
export const value = fs.readFileSync("x");
