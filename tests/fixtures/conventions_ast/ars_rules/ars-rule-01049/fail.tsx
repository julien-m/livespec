/* ARS-RULE-01049: ai-ressources/code-conventions/shadcn.md:27 #component-composition */
const fs = require("fs");
export const value = fs.readFileSync("x");
