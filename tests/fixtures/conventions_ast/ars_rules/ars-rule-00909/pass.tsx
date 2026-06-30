/* ARS-RULE-00909: ai-ressources/code-conventions/react.md:76 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
