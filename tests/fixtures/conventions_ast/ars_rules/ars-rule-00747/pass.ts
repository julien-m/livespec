/* ARS-RULE-00747: ai-ressources/code-conventions/nextjs.md:35 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
