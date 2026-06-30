/* ARS-RULE-01046: ai-ressources/code-conventions/shadcn.md:24 #component-composition */
const fs = require("fs");
export const value = fs.readFileSync("x");
