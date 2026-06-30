/* ARS-RULE-00331: ai-ressources/code-conventions/delphi.md:38 #4-use-raise-not-raise-e */
try
  DoWork;
except
  on E: Exception do raise;
end;
