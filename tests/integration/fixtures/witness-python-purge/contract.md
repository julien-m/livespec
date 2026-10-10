# Python purge witness

Implement `purge.py DIRECTORY --now EPOCH` with Python standard library.
Delete only regular, direct-child files whose mtime is at least 86400 seconds
before the supplied time, including the exact boundary. Preserve newer files,
subdirectories and symlinks. Exit zero after successful execution.
