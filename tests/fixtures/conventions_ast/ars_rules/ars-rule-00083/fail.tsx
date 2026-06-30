/* ARS-RULE-00083: ai-ressources/code-conventions/astro.md:46 #client-directives-hydration */
const fs = require("fs");
export const value = fs.readFileSync("x");
