/* ARS-RULE-00329: ai-ressources/code-conventions/delphi.md:27 #3-try-finally-for-local-objects */
try
  DoWork;
except
  on E: Exception do raise;
end;
