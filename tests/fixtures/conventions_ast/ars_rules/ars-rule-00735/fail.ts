/* ARS-RULE-00735: ai-ressources/code-conventions/nextjs.md:8 #architecture */
const fs = require("fs");
export const value = fs.readFileSync("x");
