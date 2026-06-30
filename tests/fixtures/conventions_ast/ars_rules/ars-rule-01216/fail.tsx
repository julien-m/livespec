/* ARS-RULE-01216: ai-ressources/code-conventions/tanstack.md:73 #server-functions */
const fs = require("fs");
export const value = fs.readFileSync("x");
