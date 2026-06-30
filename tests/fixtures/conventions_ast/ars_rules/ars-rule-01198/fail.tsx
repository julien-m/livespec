/* ARS-RULE-01198: ai-ressources/code-conventions/tanstack.md:40 #mutations */
const fs = require("fs");
export const value = fs.readFileSync("x");
