def load() -> str | None:
    try:
        return read_value()
    except Exception:
        return None
