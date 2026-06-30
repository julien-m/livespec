/* ARS-RULE-00745: ai-ressources/code-conventions/nextjs.md:33 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
