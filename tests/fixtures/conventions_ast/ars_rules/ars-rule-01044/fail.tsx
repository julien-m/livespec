/* ARS-RULE-01044: ai-ressources/code-conventions/shadcn.md:11 #core-principles */
const fs = require("fs");
export const value = fs.readFileSync("x");
