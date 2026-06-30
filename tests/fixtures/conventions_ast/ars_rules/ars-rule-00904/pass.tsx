/* ARS-RULE-00904: ai-ressources/code-conventions/react.md:67 #error-boundaries */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
