/* ARS-RULE-00103: ai-ressources/code-conventions/astro.md:104 #server-islands */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
