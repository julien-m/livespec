/* ARS-RULE-00777: ai-ressources/code-conventions/nextjs.md:80 #security */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
