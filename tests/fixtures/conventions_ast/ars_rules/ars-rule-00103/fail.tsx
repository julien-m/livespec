/* ARS-RULE-00103: ai-ressources/code-conventions/astro.md:104 #server-islands */
const fs = require("fs");
export const value = fs.readFileSync("x");
