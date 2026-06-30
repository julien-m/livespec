/* ARS-RULE-00767: ai-ressources/code-conventions/nextjs.md:64 #error-handling */
const fs = require("fs");
export const value = fs.readFileSync("x");
