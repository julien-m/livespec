/* ARS-RULE-00910: ai-ressources/code-conventions/react.md:77 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
