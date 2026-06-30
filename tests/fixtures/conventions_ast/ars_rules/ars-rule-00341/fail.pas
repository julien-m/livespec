/* ARS-RULE-00341: ai-ressources/code-conventions/delphi.md:54 #11-never-leak-objects-in-loops */
try
  DoWork;
except
end;
