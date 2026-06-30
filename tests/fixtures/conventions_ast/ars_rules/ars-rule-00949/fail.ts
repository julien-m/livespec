/* ARS-RULE-00949: ai-ressources/code-conventions/remotion.md:112 #performance */
const fs = require("fs");
export const value = fs.readFileSync("x");
