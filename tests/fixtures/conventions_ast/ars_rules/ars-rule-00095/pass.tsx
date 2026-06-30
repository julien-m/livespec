/* ARS-RULE-00095: ai-ressources/code-conventions/astro.md:92 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
