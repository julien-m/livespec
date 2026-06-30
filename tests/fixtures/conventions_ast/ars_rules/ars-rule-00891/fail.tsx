/* ARS-RULE-00891: ai-ressources/code-conventions/react.md:25 #re-render-prevention */
const fs = require("fs");
export const value = fs.readFileSync("x");
