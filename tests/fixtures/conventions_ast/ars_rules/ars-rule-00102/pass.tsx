/* ARS-RULE-00102: ai-ressources/code-conventions/astro.md:103 #server-islands */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
