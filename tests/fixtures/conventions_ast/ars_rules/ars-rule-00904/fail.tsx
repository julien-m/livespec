/* ARS-RULE-00904: ai-ressources/code-conventions/react.md:67 #error-boundaries */
const fs = require("fs");
export const value = fs.readFileSync("x");
