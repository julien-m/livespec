/* ARS-RULE-00778: ai-ressources/code-conventions/nextjs.md:81 #security */
const fs = require("fs");
export const value = fs.readFileSync("x");
