/* ARS-RULE-00890: ai-ressources/code-conventions/react.md:24 #re-render-prevention */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
