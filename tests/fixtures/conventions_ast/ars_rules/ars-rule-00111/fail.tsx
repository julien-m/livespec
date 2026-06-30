/* ARS-RULE-00111: ai-ressources/code-conventions/astro.md:124 #middleware */
const fs = require("fs");
export const value = fs.readFileSync("x");
