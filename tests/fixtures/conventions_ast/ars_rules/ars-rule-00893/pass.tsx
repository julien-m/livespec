/* ARS-RULE-00893: ai-ressources/code-conventions/react.md:41 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
