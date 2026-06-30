/* ARS-RULE-00346: ai-ressources/code-conventions/delphi.md:65 #14-never-swallow-exceptions */
try
  DoWork;
except
  on E: Exception do raise;
end;
