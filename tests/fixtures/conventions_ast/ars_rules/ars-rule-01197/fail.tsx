/* ARS-RULE-01197: ai-ressources/code-conventions/tanstack.md:29 #mutations */
const fs = require("fs");
export const value = fs.readFileSync("x");
