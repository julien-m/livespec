/* ARS-RULE-01199: ai-ressources/code-conventions/tanstack.md:41 #mutations */
const fs = require("fs");
export const value = fs.readFileSync("x");
