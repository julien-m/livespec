/* ARS-RULE-00741: ai-ressources/code-conventions/nextjs.md:16 #server-vs-client-components */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
