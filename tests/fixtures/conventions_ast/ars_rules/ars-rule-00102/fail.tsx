/* ARS-RULE-00102: ai-ressources/code-conventions/astro.md:103 #server-islands */
const fs = require("fs");
export const value = fs.readFileSync("x");
