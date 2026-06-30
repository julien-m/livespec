/* ARS-RULE-00095: ai-ressources/code-conventions/astro.md:92 #data-fetching */
const fs = require("fs");
export const value = fs.readFileSync("x");
