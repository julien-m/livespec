/* ARS-RULE-00882: ai-ressources/code-conventions/react.md:12 #component-design */
const fs = require("fs");
export const value = fs.readFileSync("x");
