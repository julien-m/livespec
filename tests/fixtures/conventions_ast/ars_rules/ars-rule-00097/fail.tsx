/* ARS-RULE-00097: ai-ressources/code-conventions/astro.md:94 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
