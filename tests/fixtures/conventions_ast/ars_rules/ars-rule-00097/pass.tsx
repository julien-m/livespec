/* ARS-RULE-00097: ai-ressources/code-conventions/astro.md:94 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
