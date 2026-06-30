/* ARS-RULE-00747: ai-ressources/code-conventions/nextjs.md:35 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
