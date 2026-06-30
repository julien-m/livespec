/* ARS-RULE-01042: ai-ressources/code-conventions/shadcn.md:9 #core-principles */
const fs = require("fs");
export const value = fs.readFileSync("x");
