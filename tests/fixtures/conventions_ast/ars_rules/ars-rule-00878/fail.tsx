/* ARS-RULE-00878: ai-ressources/code-conventions/react.md:8 #component-design */
const fs = require("fs");
export const value = fs.readFileSync("x");
