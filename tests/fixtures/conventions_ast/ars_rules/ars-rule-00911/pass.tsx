/* ARS-RULE-00911: ai-ressources/code-conventions/react.md:78 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
