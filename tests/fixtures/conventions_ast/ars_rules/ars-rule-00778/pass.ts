/* ARS-RULE-00778: ai-ressources/code-conventions/nextjs.md:81 #security */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
