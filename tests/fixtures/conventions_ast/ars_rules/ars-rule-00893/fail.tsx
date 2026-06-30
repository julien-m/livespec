/* ARS-RULE-00893: ai-ressources/code-conventions/react.md:41 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
