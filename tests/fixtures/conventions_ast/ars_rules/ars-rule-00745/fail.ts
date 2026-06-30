/* ARS-RULE-00745: ai-ressources/code-conventions/nextjs.md:33 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
