/* ARS-RULE-00742: ai-ressources/code-conventions/nextjs.md:17 #server-vs-client-components */
const fs = require("fs");
export const value = fs.readFileSync("x");
