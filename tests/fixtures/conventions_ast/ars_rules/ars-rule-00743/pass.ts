/* ARS-RULE-00743: ai-ressources/code-conventions/nextjs.md:18 #server-vs-client-components */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
