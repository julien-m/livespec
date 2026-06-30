/* ARS-RULE-00104: ai-ressources/code-conventions/astro.md:105 #server-islands */
const fs = require("fs");
export const value = fs.readFileSync("x");
