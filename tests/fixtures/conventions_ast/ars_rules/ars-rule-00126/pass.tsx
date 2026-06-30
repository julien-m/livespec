/* ARS-RULE-00126: ai-ressources/code-conventions/astro.md:145 #environment-variables */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
