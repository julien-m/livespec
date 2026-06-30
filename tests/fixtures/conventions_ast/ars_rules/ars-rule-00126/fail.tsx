/* ARS-RULE-00126: ai-ressources/code-conventions/astro.md:145 #environment-variables */
const fs = require("fs");
export const value = fs.readFileSync("x");
