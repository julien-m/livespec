/* ARS-RULE-00746: ai-ressources/code-conventions/nextjs.md:34 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
