/* ARS-RULE-00766: ai-ressources/code-conventions/nextjs.md:63 #error-handling */
const fs = require("fs");
export const value = fs.readFileSync("x");
