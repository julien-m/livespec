/* ARS-RULE-00104: ai-ressources/code-conventions/astro.md:105 #server-islands */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
