/* ARS-RULE-00337: ai-ressources/code-conventions/delphi.md:50 #9-prefer-const-parameters */
try
  DoWork;
except
  on E: Exception do raise;
end;
