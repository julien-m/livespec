/* ARS-RULE-01216: ai-ressources/code-conventions/tanstack.md:73 #server-functions */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
