/* ARS-RULE-00946: ai-ressources/code-conventions/remotion.md:109 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
