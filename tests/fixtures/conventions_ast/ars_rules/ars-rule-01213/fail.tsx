/* ARS-RULE-01213: ai-ressources/code-conventions/tanstack.md:67 #data-loading */
const fs = require("fs");
export const value = fs.readFileSync("x");
