/* ARS-RULE-00892: ai-ressources/code-conventions/react.md:40 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
