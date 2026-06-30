/* ARS-RULE-00890: ai-ressources/code-conventions/react.md:24 #re-render-prevention */
const fs = require("fs");
export const value = fs.readFileSync("x");
