/* ARS-RULE-00349: ai-ressources/code-conventions/delphi.md:71 #16-don-t-mix-ownership */
try
  DoWork;
except
  on E: Exception do raise;
end;
