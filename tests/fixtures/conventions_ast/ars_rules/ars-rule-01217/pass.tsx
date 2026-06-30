/* ARS-RULE-01217: ai-ressources/code-conventions/tanstack.md:85 #server-functions */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
