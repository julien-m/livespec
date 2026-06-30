/* ARS-RULE-01043: ai-ressources/code-conventions/shadcn.md:10 #core-principles */
const fs = require("fs");
export const value = fs.readFileSync("x");
