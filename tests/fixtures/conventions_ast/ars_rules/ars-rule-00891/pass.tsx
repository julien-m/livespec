/* ARS-RULE-00891: ai-ressources/code-conventions/react.md:25 #re-render-prevention */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
