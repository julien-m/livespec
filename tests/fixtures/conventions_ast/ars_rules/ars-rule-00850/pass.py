# ARS-RULE-00850: ai-ressources/code-conventions/python.md:74 #error-handling
try:
    run()
except DomainError:
    raise
