try:
    import coverage
except Exception:
    coverage = None

if coverage is not None:
    coverage.process_startup()
