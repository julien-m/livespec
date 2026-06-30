/* ARS-RULE-00353: ai-ressources/code-conventions/delphi.md:84 #pre-commit-validation */
try
  DoWork;
except
  on E: Exception do raise;
end;
