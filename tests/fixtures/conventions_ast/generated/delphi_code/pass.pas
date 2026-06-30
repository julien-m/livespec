try
  SaveRecord;
except
  on E: Exception do
    raise;
end;
