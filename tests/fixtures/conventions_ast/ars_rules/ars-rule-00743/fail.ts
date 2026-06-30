/* ARS-RULE-00743: ai-ressources/code-conventions/nextjs.md:18 #server-vs-client-components */
const fs = require("fs");
export const value = fs.readFileSync("x");
