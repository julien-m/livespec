/* ARS-RULE-00767: ai-ressources/code-conventions/nextjs.md:64 #error-handling */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
