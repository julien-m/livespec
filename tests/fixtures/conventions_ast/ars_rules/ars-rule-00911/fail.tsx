/* ARS-RULE-00911: ai-ressources/code-conventions/react.md:78 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
