/* ARS-RULE-00766: ai-ressources/code-conventions/nextjs.md:63 #error-handling */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
