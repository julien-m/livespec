/* ARS-RULE-01204: ai-ressources/code-conventions/tanstack.md:47 #configuration */
const fs = require("fs");
export const value = fs.readFileSync("x");
