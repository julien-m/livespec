/* ARS-RULE-00905: ai-ressources/code-conventions/react.md:68 #error-boundaries */
const fs = require("fs");
export const value = fs.readFileSync("x");
