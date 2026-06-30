/* ARS-RULE-00777: ai-ressources/code-conventions/nextjs.md:80 #security */
const fs = require("fs");
export const value = fs.readFileSync("x");
