/* ARS-RULE-00909: ai-ressources/code-conventions/react.md:76 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
