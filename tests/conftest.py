from lynx.arbitrator.arbitrator import LogOddsArbitrator


def pytest_configure() -> None:
    _ = LogOddsArbitrator()
