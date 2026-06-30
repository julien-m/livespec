/* ARS-RULE-00082: ai-ressources/code-conventions/astro.md:45 #client-directives-hydration */
const fs = require("fs");
export const value = fs.readFileSync("x");
