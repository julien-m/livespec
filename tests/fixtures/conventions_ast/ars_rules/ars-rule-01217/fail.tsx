/* ARS-RULE-01217: ai-ressources/code-conventions/tanstack.md:85 #server-functions */
const fs = require("fs");
export const value = fs.readFileSync("x");
