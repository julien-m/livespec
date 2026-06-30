/* ARS-RULE-00742: ai-ressources/code-conventions/nextjs.md:17 #server-vs-client-components */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
