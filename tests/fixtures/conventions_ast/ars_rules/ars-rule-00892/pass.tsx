/* ARS-RULE-00892: ai-ressources/code-conventions/react.md:40 #data-fetching */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
