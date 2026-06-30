def load() -> str:
    try:
        return read_value()
    except ValueError:
        raise
