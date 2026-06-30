/* ARS-RULE-00746: ai-ressources/code-conventions/nextjs.md:34 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
