/* ARS-RULE-00947: ai-ressources/code-conventions/remotion.md:110 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
