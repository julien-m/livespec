/* ARS-RULE-00741: ai-ressources/code-conventions/nextjs.md:16 #server-vs-client-components */
const fs = require("fs");
export const value = fs.readFileSync("x");
