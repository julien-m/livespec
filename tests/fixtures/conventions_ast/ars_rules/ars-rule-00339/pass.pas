/* ARS-RULE-00339: ai-ressources/code-conventions/delphi.md:52 #10-avoid-unnecessary-temporaries */
try
  DoWork;
except
  on E: Exception do raise;
end;
