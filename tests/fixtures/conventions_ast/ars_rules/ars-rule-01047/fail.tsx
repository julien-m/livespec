/* ARS-RULE-01047: ai-ressources/code-conventions/shadcn.md:25 #component-composition */
const fs = require("fs");
export const value = fs.readFileSync("x");
