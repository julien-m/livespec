/* ARS-RULE-00065: ai-ressources/code-conventions/astro.md:8 #architecture */
const fs = require("fs");
export const value = fs.readFileSync("x");
