/* ARS-RULE-00928: ai-ressources/code-conventions/remotion.md:75 #sequencing */
const fs = require("fs");
export const value = fs.readFileSync("x");
