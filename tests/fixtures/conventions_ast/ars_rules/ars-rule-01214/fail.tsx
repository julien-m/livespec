/* ARS-RULE-01214: ai-ressources/code-conventions/tanstack.md:68 #data-loading */
const fs = require("fs");
export const value = fs.readFileSync("x");
