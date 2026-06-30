/* ARS-RULE-00910: ai-ressources/code-conventions/react.md:77 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
