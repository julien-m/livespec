/* ARS-RULE-00773: ai-ressources/code-conventions/nextjs.md:74 #caching-revalidation */
const fs = require("fs");
export const value = fs.readFileSync("x");
